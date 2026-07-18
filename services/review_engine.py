"""
Review Rule Engine (CV Engineer will complete implementation).

Evaluates detection results against configurable review rules and produces
a verdict: pass / review / reject.
"""
from typing import Dict, Optional


DEFAULT_SETTINGS = {
    'risk_classes': ['person'],
    'reject_confidence': 0.60,
    'review_confidence': 0.35,
    'min_evidence_frames': 1,
}


def evaluate(detection_result: Dict, settings: Optional[Dict] = None) -> Dict:
    """
    Apply review rules to detection results.

    Args:
        detection_result: Output from detect()
        settings: Review rule settings (uses DEFAULT_SETTINGS if None)

    Returns:
        Evaluation result with verdict and supporting data.

    Rules (priority order):
      1. risk_class + confidence >= reject_confidence → reject
      2. risk_class + confidence >= review_confidence → review
         OR results unstable across frames → review
      3. Otherwise → pass
    """
    applied = settings or DEFAULT_SETTINGS

    # STUB: Always return pass until CV Engineer implements
    return {
        'verdict': 'pass',
        'verdict_reason': '未发现风险目标 — 等待CV算法工程师完成模型集成',
        'risk_detections': [],
        'evidence_frames': [],
        'statistics': {
            'total_frames': detection_result.get('total_frames_analyzed', 0),
            'frames_with_detections': 0,
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'low_confidence_count': 0,
        },
        'applied_settings': applied,
    }


def format_report(
    detection_result: Dict,
    evaluation_result: Dict,
    job_info: Dict
) -> Dict:
    """
    Build the final analysis_report.json structure.

    Args:
        detection_result: Output from detect()
        evaluation_result: Output from evaluate()
        job_info: job.json contents

    Returns:
        Complete analysis report dict.
    """
    from datetime import datetime

    return {
        'job_id': job_info.get('job_id', ''),
        'project_name': job_info.get('project_name', ''),
        'asset_name': job_info.get('asset_name', ''),
        'analyzed_at': datetime.now().isoformat(),
        'input_type': detection_result.get('input_type', 'unknown'),
        'auto_verdict': evaluation_result.get('verdict', 'pass'),
        'auto_verdict_reason': evaluation_result.get('verdict_reason', ''),
        'manual_review': None,
        'detection_summary': detection_result.get('summary', {}),
        'risk_detections': evaluation_result.get('risk_detections', []),
        'evidence_frames': evaluation_result.get('evidence_frames', []),
        'statistics': evaluation_result.get('statistics', {}),
        'applied_settings': evaluation_result.get('applied_settings', {}),
    }
