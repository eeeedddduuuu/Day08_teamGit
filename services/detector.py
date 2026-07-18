"""
YOLO 检测器封装 — 单例模式，支持图片和视频检测。

供 backend 的 _run_analysis 调用 module-level detect() 函数。
"""
import os
import cv2
import tempfile
from typing import List, Dict, Optional
from ultralytics import YOLO


class Detector:
    """YOLO 检测器单例"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self, model_path: str = "models/yolo11n.pt") -> bool:
        """
        加载 YOLO 模型。返回 True/False，不抛异常。

        Args:
            model_path: 模型文件路径

        Returns:
            bool: 加载成功返回 True
        """
        try:
            if not os.path.exists(model_path):
                print(f"[Detector] 模型文件不存在: {model_path}")
                return False
            self._model = YOLO(model_path)
            # 预热模型（使用空白 numpy 数组，避免空字符串导致的异常）
            try:
                import numpy as np
                dummy = np.zeros((64, 64, 3), dtype=np.uint8)
                _ = self._model.predict(source=dummy, verbose=False)
            except Exception:
                pass  # 预热失败不影响后续使用
            print(f"[Detector] 模型加载成功: {model_path}")
            return True
        except Exception as e:
            print(f"[Detector] 模型加载失败: {e}")
            self._model = None
            return False

    @property
    def is_ready(self) -> bool:
        """模型是否已加载"""
        return self._model is not None

    def detect_image(self, image_path: str) -> List[Dict]:
        """
        对单张图片做检测。

        Args:
            image_path: 图片文件路径

        Returns:
            [
                {
                    "class": "person",        # 类别名
                    "class_id": 0,             # 类别 ID
                    "confidence": 0.85,        # 置信度 float
                    "bbox": [x1, y1, x2, y2]   # 边界框 int
                },
                ...
            ]
            异常时返回空列表 []，不抛异常。
        """
        if not self.is_ready:
            print("[Detector] 模型未加载，无法检测")
            return []

        try:
            results = self._model.predict(
                source=image_path,
                verbose=False
            )
        except Exception as e:
            print(f"[Detector] 图片检测异常: {e}")
            return []

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                xyxy = boxes.xyxy[i].tolist()
                bbox = [int(round(v)) for v in xyxy]

                # 获取类别名（COCO 数据集）
                class_name = self._model.names.get(cls_id, f"class_{cls_id}")

                detections.append({
                    "class": class_name,
                    "class_id": cls_id,
                    "confidence": round(conf, 4),
                    "bbox": bbox
                })

        return detections

    def detect_video(
        self, video_path: str, sample_interval: float = 1.0
    ) -> List[Dict]:
        """
        对视频按时间间隔采样并检测。

        Args:
            video_path: 视频文件路径
            sample_interval: 采样间隔（秒），默认 1 秒

        Returns:
            [
                {
                    "frame_index": 0,
                    "timestamp": 0.0,        # 秒
                    "detections": [...]       # 同 detect_image 返回格式
                },
                ...
            ]
            异常时返回空列表 []，不抛异常。
        """
        if not self.is_ready:
            print("[Detector] 模型未加载，无法检测")
            return []

        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"[Detector] 无法打开视频: {video_path}")
                return []

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if fps <= 0:
                fps = 30.0  # 回退默认值

            frame_interval = max(1, int(fps * sample_interval))

            frame_results = []
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 按采样间隔提取帧
                if frame_idx % frame_interval == 0:
                    timestamp = round(frame_idx / fps, 2)

                    # 将帧临时保存为图片用于 YOLO 检测
                    # 使用系统临时目录，避免污染工作目录
                    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                    os.close(temp_fd)
                    cv2.imwrite(temp_path, frame)

                    detections = self.detect_image(temp_path)

                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                    frame_results.append({
                        "frame_index": frame_idx,
                        "timestamp": timestamp,
                        "detections": detections
                    })

                frame_idx += 1

            cap.release()
            return frame_results

        except Exception as e:
            print(f"[Detector] 视频检测异常: {e}")
            if cap is not None:
                cap.release()
            return []


# ── 模块级便捷函数 ────────────────────────────────────────────


def detect(file_path: str, job_dir: str) -> Dict:
    """
    主入口函数，供 backend 的 _run_analysis 调用。

    自动判断输入类型（图片/视频），执行检测，保存证据帧，
    返回结构化的检测结果。

    Args:
        file_path: 输入文件路径 (outputs/<job_id>/input/<filename>)
        job_dir:   任务目录 (outputs/<job_id>/)

    Returns:
        {
            "input_type": "image" | "video",
            "file_name": "xxx.jpg",
            "total_frames_analyzed": 10,
            "frame_results": [...],
            "evidence_frames": ["keyframes/frame_0000.jpg", ...],
            "summary": {
                "total_detections": 45,
                "classes_detected": {"person": 30, "car": 15},
                "max_confidence": 0.92,
                "avg_confidence": 0.67
            }
        }
    """
    # 判断输入类型
    ext = os.path.splitext(file_path)[1].lower()
    video_exts = {".mp4", ".avi", ".mov", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png"}
    input_type = "video" if ext in video_exts else "image"

    file_name = os.path.basename(file_path)

    # 获取检测器单例
    detector = Detector()
    if not detector.is_ready:
        detector.load_model()

    # 创建证据帧目录
    keyframes_dir = os.path.join(job_dir, "keyframes")
    os.makedirs(keyframes_dir, exist_ok=True)

    # 执行检测
    if input_type == "image":
        detections = detector.detect_image(file_path)
        frame_results = [
            {
                "frame_index": 0,
                "timestamp": 0.0,
                "detections": detections
            }
        ]
        # 保存证据帧（图片本身 + 检测框）
        evidence_path = os.path.join(keyframes_dir, "frame_0000.jpg")
        img = cv2.imread(file_path)
        if img is not None:
            if detections:
                img = _draw_boxes(img, detections)
            cv2.imwrite(evidence_path, img)
        evidence_frames = ["keyframes/frame_0000.jpg"]
    else:
        frame_results = detector.detect_video(file_path, sample_interval=1.0)
        # 保存证据帧（有检测结果的帧）
        evidence_frames = _save_evidence_frames(
            file_path, frame_results, keyframes_dir
        )

    # 汇总统计
    summary = _compute_summary(frame_results)

    return {
        "input_type": input_type,
        "file_name": file_name,
        "total_frames_analyzed": len(frame_results),
        "frame_results": frame_results,
        "evidence_frames": evidence_frames,
        "summary": summary
    }


def _draw_boxes(image, detections):
    """在图片上绘制检测框和标签。"""
    import cv2 as cv
    img = image.copy()
    colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
    for i, det in enumerate(detections):
        x1, y1, x2, y2 = det["bbox"]
        label = f"{det['class']} {det['confidence']:.2f}"
        color = colors[i % len(colors)]
        cv.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv.putText(img, label, (x1, max(y1 - 5, 15)), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return img


def _save_evidence_frames(
    video_path: str,
    frame_results: List[Dict],
    keyframes_dir: str,
    max_frames: int = 10
) -> List[str]:
    """
    保存证据帧图片。优先保存置信度最高的帧。

    Args:
        video_path: 视频文件路径
        frame_results: 检测结果
        keyframes_dir: 证据帧保存目录
        max_frames: 最多保存帧数

    Returns:
        ["keyframes/frame_0005.jpg", ...]  相对路径列表
    """
    # 选出有检测结果的帧，按最高置信度排序
    scored_frames = []
    for fr in frame_results:
        if not fr["detections"]:
            continue
        max_conf = max(d["confidence"] for d in fr["detections"])
        scored_frames.append((max_conf, fr["frame_index"]))

    # 按置信度降序排序，取前 max_frames
    scored_frames.sort(key=lambda x: x[0], reverse=True)
    top_indices = {sf[1] for sf in scored_frames[:max_frames]}

    evidence_frames = []
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return evidence_frames

        frame_idx = 0
        saved = 0
        while saved < len(top_indices):
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in top_indices:
                filename = f"frame_{frame_idx:04d}.jpg"
                save_path = os.path.join(keyframes_dir, filename)
                # 查找当前帧的检测结果并绘制框
                fr = next((f for f in frame_results if f["frame_index"] == frame_idx), None)
                if fr and fr.get("detections"):
                    frame = _draw_boxes(frame, fr["detections"])
                cv2.imwrite(save_path, frame)
                evidence_frames.append(f"keyframes/{filename}")
                saved += 1
            frame_idx += 1

        cap.release()
    except Exception as e:
        print(f"[Detector] 保存证据帧异常: {e}")
        if cap is not None:
            cap.release()

    return evidence_frames


def _compute_summary(frame_results: List[Dict]) -> Dict:
    """
    计算检测结果汇总统计。

    Args:
        frame_results: 所有帧的检测结果

    Returns:
        {
            "total_detections": 45,
            "classes_detected": {"person": 30, "car": 15},
            "max_confidence": 0.92,
            "avg_confidence": 0.67
        }
    """
    all_detections = []
    for fr in frame_results:
        all_detections.extend(fr["detections"])

    if not all_detections:
        return {
            "total_detections": 0,
            "classes_detected": {},
            "max_confidence": 0.0,
            "avg_confidence": 0.0
        }

    # 按类别统计
    classes_detected = {}
    for d in all_detections:
        cls = d["class"]
        classes_detected[cls] = classes_detected.get(cls, 0) + 1

    confidences = [d["confidence"] for d in all_detections]

    return {
        "total_detections": len(all_detections),
        "classes_detected": classes_detected,
        "max_confidence": round(max(confidences), 4),
        "avg_confidence": round(sum(confidences) / len(confidences), 4)
    }
