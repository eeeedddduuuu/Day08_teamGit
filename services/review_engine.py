"""
审核规则引擎 — 根据 YOLO 检测结果，按三级规则输出审核结论。

审核规则（按优先级）:
    1. reject: 风险类别 + 置信度 >= reject_confidence
    2. review: 风险类别 + 置信度 >= review_confidence（但 < reject_confidence）
       或 同一类别在帧间置信度波动 > 0.4
    3. pass:   其余情况
"""
from typing import Dict, List, Optional
from datetime import datetime


# ── 默认审核配置 ────────────────────────────────────────────

DEFAULT_SETTINGS = {
    "risk_classes": ["person"],
    "reject_confidence": 0.60,
    "review_confidence": 0.35,
    "min_evidence_frames": 1
}


# ── 审核规则引擎 ────────────────────────────────────────────

def evaluate(
    detection_result: Dict,
    settings: Optional[Dict] = None
) -> Dict:
    """
    根据检测结果和审核规则，输出审核结论。

    Args:
        detection_result: detect() 的返回值
        settings:         审核规则配置（可选，默认使用 DEFAULT_SETTINGS）

    Returns:
        {
            "verdict": "pass" | "review" | "reject",
            "verdict_reason": "发现高风险类别 person，置信度 0.85 >= 0.60",
            "risk_detections": [...],
            "evidence_frames": [...],
            "statistics": {...},
            "applied_settings": {...}
        }
    """
    if settings is None:
        settings = DEFAULT_SETTINGS.copy()

    risk_classes = settings.get("risk_classes", ["person"])
    reject_conf = settings.get("reject_confidence", 0.60)
    review_conf = settings.get("review_confidence", 0.35)

    frame_results = detection_result.get("frame_results", [])
    evidence_frames_all = detection_result.get("evidence_frames", [])

    # ── 1. 收集所有风险检测 ──────────────────────────────
    reject_candidates = []   # 达到 reject 阈值的检测
    review_candidates = []   # 达到 review 阈值的检测
    all_risk_detections = []  # 所有风险类别的检测（用于稳定性分析）

    for fr in frame_results:
        for det in fr.get("detections", []):
            cls = det.get("class", "")
            conf = det.get("confidence", 0.0)

            if cls not in risk_classes:
                continue

            risk_item = {
                "frame_index": fr.get("frame_index", 0),
                "timestamp": fr.get("timestamp", 0.0),
                "class": cls,
                "confidence": conf,
                "bbox": det.get("bbox", [])
            }

            all_risk_detections.append(risk_item)

            if conf >= reject_conf:
                reject_candidates.append(risk_item)
            elif conf >= review_conf:
                review_candidates.append(risk_item)

    # ── 2. 检查帧间稳定性 ─────────────────────────────────
    is_unstable = _check_instability(frame_results, risk_classes, review_conf)

    # ── 3. 判定结论 ───────────────────────────────────────
    if reject_candidates:
        # 取置信度最高的 reject 检测作为理由
        best = max(reject_candidates, key=lambda x: x["confidence"])
        verdict = "reject"
        verdict_reason = (
            f"发现高风险类别 {best['class']}，"
            f"置信度 {best['confidence']} >= {reject_conf}"
        )
        risk_detections = reject_candidates

    elif review_candidates or is_unstable:
        if review_candidates:
            best = max(review_candidates, key=lambda x: x["confidence"])
            verdict = "review"
            verdict_reason = (
                f"发现风险类别 {best['class']}，"
                f"置信度 {best['confidence']} 在 [{review_conf}, {reject_conf}) 区间"
            )
        else:
            verdict = "review"
            verdict_reason = "同一类别置信度在帧间波动 > 0.4，检测结果不稳定"

        risk_detections = review_candidates + (
            all_risk_detections if is_unstable else []
        )
        # 去重
        seen = set()
        risk_detections = [
            d for d in risk_detections
            if not (d["frame_index"], d["class"], d["confidence"]) in seen
            and not seen.add((d["frame_index"], d["class"], d["confidence"]))
        ]

    else:
        verdict = "pass"
        verdict_reason = "未发现风险类别目标，素材正常"
        risk_detections = []

    # ── 4. 确定证据帧（置信度最高的 1~3 帧） ──────────────
    evidence_frames = _select_evidence_frames(
        risk_detections, evidence_frames_all,
        min_frames=settings.get("min_evidence_frames", 1)
    )

    # ── 5. 计算统计信息 ───────────────────────────────────
    statistics = _compute_statistics(
        frame_results, risk_classes, reject_conf, review_conf
    )

    return {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "risk_detections": risk_detections,
        "evidence_frames": evidence_frames,
        "statistics": statistics,
        "applied_settings": settings
    }


def format_report(
    detection_result: Dict,
    evaluation_result: Dict,
    job_info: Dict
) -> Dict:
    """
    生成最终的 analysis_report.json 结构。

    Args:
        detection_result:  detect() 的返回值
        evaluation_result: evaluate() 的返回值
        job_info:          任务元信息（含 job_id, project_name, asset_name）

    Returns:
        完整的审核报告 dict，可直接序列化为 analysis_report.json
    """
    return {
        "job_id": job_info.get("job_id", ""),
        "project_name": job_info.get("project_name", ""),
        "asset_name": job_info.get("asset_name", ""),
        "analyzed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "input_type": detection_result.get("input_type", "unknown"),
        "auto_verdict": evaluation_result.get("verdict", "pass"),
        "auto_verdict_reason": evaluation_result.get("verdict_reason", ""),
        "manual_review": None,
        "detection_summary": detection_result.get("summary", {}),
        "risk_detections": evaluation_result.get("risk_detections", []),
        "evidence_frames": evaluation_result.get("evidence_frames", []),
        "statistics": evaluation_result.get("statistics", {}),
        "applied_settings": evaluation_result.get("applied_settings", {})
    }


# ── 内部辅助函数 ────────────────────────────────────────────

def _check_instability(
    frame_results: List[Dict],
    risk_classes: List[str],
    review_conf: float
) -> bool:
    """
    检查同一风险类别在不同帧间的置信度是否波动过大（> 0.4）。

    判定标准：同一类别在任意两帧之间的置信度差异 > 0.4，且
    至少一帧的置信度 >= review_confidence（确保低置信度噪声不被误判）。

    Returns:
        bool: 是否检测到不稳定
    """
    # 按类别收集各帧置信度
    class_confidences = {}
    for fr in frame_results:
        frame_idx = fr.get("frame_index", 0)
        for det in fr.get("detections", []):
            cls = det.get("class", "")
            if cls not in risk_classes:
                continue
            conf = det.get("confidence", 0.0)
            if cls not in class_confidences:
                class_confidences[cls] = []
            class_confidences[cls].append((frame_idx, conf))

    for cls, values in class_confidences.items():
        if len(values) < 2:
            continue
        confs = [v[1] for v in values]
        max_c, min_c = max(confs), min(confs)
        if max_c - min_c > 0.4 and max_c >= review_conf:
            return True

    return False


def _select_evidence_frames(
    risk_detections: List[Dict],
    evidence_frames_all: List[str],
    min_frames: int = 1
) -> List[str]:
    """
    从风险检测中选出置信度最高的帧作为证据帧。

    Args:
        risk_detections:    触发风险的检测列表
        evidence_frames_all: 所有已保存的证据帧路径
        min_frames:         最少证据帧数

    Returns:
        筛选后的证据帧路径列表（1~3 个）
    """
    if not risk_detections:
        # 没有风险检测时，返回前 min_frames 个证据帧（如果有的话）
        return evidence_frames_all[:max(1, min_frames)]

    # 按帧去重，每帧取最高置信度
    frame_best = {}
    for d in risk_detections:
        fi = d["frame_index"]
        if fi not in frame_best or d["confidence"] > frame_best[fi]:
            frame_best[fi] = d["confidence"]

    # 按置信度降序排序
    sorted_frames = sorted(frame_best.items(), key=lambda x: x[1], reverse=True)

    # 取前 3 帧，但不少于 min_frames
    top_count = max(min_frames, min(3, len(sorted_frames)))
    top_indices = {sf[0] for sf in sorted_frames[:top_count]}

    # 从 evidence_frames_all 中匹配
    selected = []
    for ef in evidence_frames_all:
        # 从文件名提取 frame_index
        for fi in top_indices:
            if f"frame_{fi:04d}" in ef or f"_{fi:04d}." in ef:
                selected.append(ef)
                break

    return selected


def _compute_statistics(
    frame_results: List[Dict],
    risk_classes: List[str],
    reject_conf: float,
    review_conf: float
) -> Dict:
    """
    计算审核统计信息。

    Returns:
        {
            "total_frames": 10,
            "frames_with_detections": 7,
            "high_confidence_count": 3,
            "medium_confidence_count": 4,
            "low_confidence_count": 0
        }
    """
    total_frames = len(frame_results)
    frames_with_detections = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    for fr in frame_results:
        dets = fr.get("detections", [])
        if dets:
            frames_with_detections += 1

        for det in dets:
            cls = det.get("class", "")
            if cls not in risk_classes:
                continue
            conf = det.get("confidence", 0.0)
            if conf >= reject_conf:
                high_count += 1
            elif conf >= review_conf:
                medium_count += 1
            else:
                low_count += 1

    return {
        "total_frames": total_frames,
        "frames_with_detections": frames_with_detections,
        "high_confidence_count": high_count,
        "medium_confidence_count": medium_count,
        "low_confidence_count": low_count
    }
