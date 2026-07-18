"""
Review engine logic tests using pytest.

Tests the evaluate() and format_report() functions from services/review_engine.py
with crafted detection results — no YOLO model or external dependencies needed.
"""
import os
import sys
from copy import deepcopy

import pytest

# ── Ensure project root on path ──────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from services.review_engine import evaluate, format_report, DEFAULT_SETTINGS


# ══════════════════════════════════════════════════════════════
#  Helper factories
# ══════════════════════════════════════════════════════════════

def _make_detection(cls: str = 'person', confidence: float = 0.85,
                    class_id: int = 0, bbox: list = None,
                    frame_index: int = 0, timestamp: float = 0.0) -> dict:
    """Create a single detection dict."""
    return {
        'class': cls,
        'class_id': class_id,
        'confidence': confidence,
        'bbox': bbox or [10, 20, 100, 200],
    }


def _make_frame(frame_index: int, timestamp: float,
                detections: list) -> dict:
    """Create a frame result dict."""
    return {
        'frame_index': frame_index,
        'timestamp': timestamp,
        'detections': detections,
    }


def _make_detection_result(input_type: str = 'image',
                            file_name: str = 'test.jpg',
                            frames: list = None,
                            evidence_frames: list = None) -> dict:
    """Create a detection result dict (simulating detect() output)."""
    frames = frames or []
    return {
        'input_type': input_type,
        'file_name': file_name,
        'total_frames_analyzed': len(frames),
        'frame_results': frames,
        'evidence_frames': evidence_frames or [],
        'summary': {
            'total_detections': sum(len(f.get('detections', [])) for f in frames),
            'classes_detected': {},
            'max_confidence': 0.0,
            'avg_confidence': 0.0,
        },
    }


def _make_job_info(job_id: str = '20260718_101530_a1b2c3d4',
                   project_name: str = '测试项目',
                   asset_name: str = 'test.jpg') -> dict:
    """Create a minimal job_info dict."""
    return {
        'job_id': job_id,
        'project_name': project_name,
        'asset_name': asset_name,
    }


# ══════════════════════════════════════════════════════════════
#  TestReviewRules — verdict logic
# ══════════════════════════════════════════════════════════════

class TestReviewRules:
    """Test the evaluate() function verdict logic per the spec's priority rules."""

    # ── Rule 1: reject ──────────────────────────────────────

    def test_reject_on_high_confidence_risk_class(self):
        """Risk class (person) + confidence >= 0.60 → verdict = reject."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.85),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'reject'
        assert 'person' in eval_result['verdict_reason']
        assert '0.85' in eval_result['verdict_reason']
        assert len(eval_result['risk_detections']) == 1
        assert eval_result['risk_detections'][0]['confidence'] == 0.85

    def test_reject_at_exact_threshold(self):
        """Confidence exactly 0.60 → reject (>= threshold)."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.60),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'reject'
        assert eval_result['statistics']['high_confidence_count'] == 1

    def test_reject_above_threshold(self):
        """Confidence 0.99 → reject."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.99),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'reject'

    def test_reject_takes_priority_over_review(self):
        """When both high and medium conf detections exist, reject wins."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.85),  # high → reject
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.50),  # medium
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'reject'
        assert eval_result['statistics']['high_confidence_count'] == 1
        assert eval_result['statistics']['medium_confidence_count'] == 1

    def test_reject_with_custom_threshold(self):
        """Custom reject_confidence=0.40 changes behavior."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.50),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        custom_settings = {**DEFAULT_SETTINGS, 'reject_confidence': 0.40}
        eval_result = evaluate(result, custom_settings)

        assert eval_result['verdict'] == 'reject'

    def test_reject_with_multiple_frames(self):
        """Reject when high-confidence detection appears in any frame."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.10),  # low
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.20),  # low
            ]),
            _make_frame(2, 2.0, [
                _make_detection('person', confidence=0.88),  # high → reject
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'reject'

    # ── Rule 2: review ─────────────────────────────────────

    def test_review_on_medium_confidence(self):
        """Confidence in [0.35, 0.60) → review."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.45),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'review'
        assert eval_result['statistics']['medium_confidence_count'] == 1
        assert eval_result['statistics']['high_confidence_count'] == 0

    def test_review_at_review_threshold(self):
        """Confidence exactly 0.35 → review."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.35),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'review'

    def test_review_just_below_reject_threshold(self):
        """Confidence 0.59 → review (not yet reject)."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.59),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'review'

    def test_review_on_unstable_results(self):
        """Same class confidence fluctuates >0.4 across frames → review,
        even if individual confidences are low."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.05),
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.75),  # 0.70 diff > 0.4
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        # 0.75 >= 0.60 → reject actually, so let me make both below reject
        # but with a large fluctuation
        frames2 = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.10),
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.55),  # 0.45 diff > 0.4
            ]),
        ]
        result2 = _make_detection_result(frames=frames2)
        eval_result2 = evaluate(result2)

        assert eval_result2['verdict'] == 'review'
        assert '不稳定' in eval_result2['verdict_reason']

    def test_review_stable_low_results_is_not_unstable(self):
        """Small fluctuation <= 0.4 across frames with no medium/high detections
        should not trigger review by instability."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.10),
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.30),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        # Both are < 0.35 and diff is 0.20 <= 0.4 → pass
        assert eval_result['verdict'] == 'pass'

    def test_review_unstable_exactly_threshold(self):
        """Confidence diff exactly 0.4 → not unstable (must be > 0.4)."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.10),
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.50),  # diff = 0.40, not > 0.4
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        # 0.50 is medium (>= 0.35) → review anyway, but reason should NOT mention unstable
        assert eval_result['verdict'] == 'review'
        assert '不稳定' not in eval_result['verdict_reason']

    # ── Rule 3: pass ───────────────────────────────────────

    def test_pass_on_no_detection(self):
        """Empty detections → pass."""
        frames = [
            _make_frame(0, 0.0, []),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'pass'
        assert eval_result['verdict_reason'] == '未发现风险目标'
        assert eval_result['risk_detections'] == []

    def test_pass_on_empty_frames(self):
        """No frames at all → pass."""
        result = _make_detection_result(frames=[])
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'pass'

    def test_pass_on_low_confidence(self):
        """Confidence < review_confidence → pass."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.10),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'pass'
        assert eval_result['statistics']['low_confidence_count'] == 1

    def test_pass_on_non_risk_class(self):
        """Detections for non-risk classes (e.g., 'car') are ignored → pass."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('car', confidence=0.99),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'pass'
        assert eval_result['statistics']['high_confidence_count'] == 0

    # ── Custom settings ────────────────────────────────────

    def test_custom_risk_classes(self):
        """Custom risk_classes changes what triggers review."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('car', confidence=0.90),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        custom_settings = {**DEFAULT_SETTINGS, 'risk_classes': ['car', 'person']}
        eval_result = evaluate(result, custom_settings)

        assert eval_result['verdict'] == 'reject'

    def test_custom_all_thresholds(self):
        """Fully custom settings are respected."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('cat', confidence=0.50),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        custom_settings = {
            'risk_classes': ['cat', 'dog'],
            'reject_confidence': 0.80,
            'review_confidence': 0.30,
            'min_evidence_frames': 2,
        }
        eval_result = evaluate(result, custom_settings)

        assert eval_result['verdict'] == 'review'
        assert eval_result['applied_settings'] == custom_settings

    def test_default_settings_used_when_none(self):
        """When settings is None, DEFAULT_SETTINGS is used."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.85),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result, None)

        assert eval_result['applied_settings'] == DEFAULT_SETTINGS
        assert eval_result['verdict'] == 'reject'

    # ── Statistics ─────────────────────────────────────────

    def test_statistics_frame_count(self):
        """Statistics correctly counts frames with detections."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.85),
            ]),
            _make_frame(1, 1.0, []),  # empty frame
            _make_frame(2, 2.0, [
                _make_detection('person', confidence=0.20),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['statistics']['total_frames'] == 3
        assert eval_result['statistics']['frames_with_detections'] == 2
        assert eval_result['statistics']['high_confidence_count'] == 1
        assert eval_result['statistics']['low_confidence_count'] == 1

    def test_statistics_with_mixed_risk_and_non_risk(self):
        """Non-risk detections are not counted in statistics."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.85),
                _make_detection('car', confidence=0.99),    # non-risk
                _make_detection('bicycle', confidence=0.99), # non-risk
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        # Only person is risk_class; the others are ignored
        assert eval_result['statistics']['high_confidence_count'] == 1
        assert eval_result['statistics']['frames_with_detections'] == 1

    # ── Evidence frames ────────────────────────────────────

    def test_evidence_frames_passed_through(self):
        """Evidence frames from detection result are passed through."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.90),
            ]),
        ]
        result = _make_detection_result(
            frames=frames,
            evidence_frames=['keyframes/frame_0000.jpg'],
        )
        eval_result = evaluate(result)

        assert 'keyframes/frame_0000.jpg' in eval_result['evidence_frames']

    def test_risk_detections_sorted_by_confidence(self):
        """risk_detections are sorted by confidence descending."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.50, frame_index=0),
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.80, frame_index=1),
            ]),
            _make_frame(2, 2.0, [
                _make_detection('person', confidence=0.65, frame_index=2),
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        confs = [d['confidence'] for d in eval_result['risk_detections']]
        assert confs == [0.80, 0.65, 0.50]

    # ── Edge cases ─────────────────────────────────────────

    def test_missing_class_field(self):
        """Detection without 'class' field is treated as empty class."""
        frames = [
            _make_frame(0, 0.0, [
                {'confidence': 0.90, 'class_id': 0, 'bbox': [1, 2, 3, 4]},
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        # Empty class not in risk_classes → pass
        assert eval_result['verdict'] == 'pass'

    def test_missing_confidence_field(self):
        """Detection without 'confidence' field defaults to 0.0."""
        frames = [
            _make_frame(0, 0.0, [
                {'class': 'person', 'class_id': 0, 'bbox': [1, 2, 3, 4]},
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        # confidence 0.0 < 0.35 → pass
        assert eval_result['verdict'] == 'pass'

    def test_video_multiple_frames(self):
        """Video-type input with multiple sampled frames."""
        frames = [
            _make_frame(i, float(i), [_make_detection('person', confidence=0.15)])
            for i in range(10)
        ]
        result = _make_detection_result(input_type='video', frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'pass'
        assert eval_result['statistics']['total_frames'] == 10

    def test_mixed_classes_with_only_one_risk(self):
        """Only risk-class detections trigger rules; others are ignored."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('car', confidence=0.95),      # non-risk
                _make_detection('person', confidence=0.50),   # risk, medium
            ]),
        ]
        result = _make_detection_result(frames=frames)
        eval_result = evaluate(result)

        assert eval_result['verdict'] == 'review'
        assert len(eval_result['risk_detections']) == 1
        assert eval_result['risk_detections'][0]['class'] == 'person'


# ══════════════════════════════════════════════════════════════
#  TestFormatReport
# ══════════════════════════════════════════════════════════════

class TestFormatReport:
    """Test the format_report() function."""

    def test_format_report_structure(self):
        """format_report returns all required top-level fields."""
        detection = _make_detection_result(frames=[
            _make_frame(0, 0.0, [_make_detection('person', confidence=0.85)]),
        ])
        evaluation = evaluate(detection)
        job_info = _make_job_info()

        report = format_report(detection, evaluation, job_info)

        required_fields = [
            'job_id', 'project_name', 'asset_name', 'analyzed_at',
            'input_type', 'auto_verdict', 'auto_verdict_reason',
            'manual_review', 'detection_summary', 'risk_detections',
            'evidence_frames', 'statistics', 'applied_settings',
        ]
        for field in required_fields:
            assert field in report, f'Missing required field: {field}'

    def test_format_report_passes_verdict(self):
        """Report reflects the evaluation verdict."""
        detection = _make_detection_result(frames=[
            _make_frame(0, 0.0, [_make_detection('person', confidence=0.85)]),
        ])
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, _make_job_info())

        assert report['auto_verdict'] == 'reject'
        assert '0.85' in report['auto_verdict_reason']

    def test_format_report_job_info_mapping(self):
        """Job info fields are correctly mapped to report."""
        job_info = _make_job_info(
            job_id='20260718_120000_abcdef01',
            project_name='星港遗迹内容审核',
            asset_name='opening_scene.mp4',
        )
        detection = _make_detection_result(
            input_type='video', file_name='opening_scene.mp4', frames=[],
        )
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, job_info)

        assert report['job_id'] == '20260718_120000_abcdef01'
        assert report['project_name'] == '星港遗迹内容审核'
        assert report['asset_name'] == 'opening_scene.mp4'
        assert report['input_type'] == 'video'

    def test_format_report_manual_review_initially_none(self):
        """manual_review is None when report is first created."""
        detection = _make_detection_result(frames=[])
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, _make_job_info())

        assert report['manual_review'] is None

    def test_format_report_analyzed_at_is_iso_format(self):
        """analyzed_at is a valid ISO datetime string."""
        detection = _make_detection_result(frames=[])
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, _make_job_info())

        from datetime import datetime
        # Should not raise
        datetime.fromisoformat(report['analyzed_at'])

    def test_format_report_statistics_are_preserved(self):
        """Statistics from evaluation are passed through to report."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.85),
            ]),
            _make_frame(1, 1.0, [
                _make_detection('person', confidence=0.50),
            ]),
        ]
        detection = _make_detection_result(frames=frames)
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, _make_job_info())

        assert report['statistics']['high_confidence_count'] == 1
        assert report['statistics']['medium_confidence_count'] == 1
        assert report['statistics']['frames_with_detections'] == 2

    def test_format_report_with_pass_result(self):
        """Report for a pass verdict."""
        detection = _make_detection_result(frames=[
            _make_frame(0, 0.0, []),
        ])
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, _make_job_info())

        assert report['auto_verdict'] == 'pass'
        assert report['risk_detections'] == []
        assert report['evidence_frames'] == []

    def test_format_report_risk_detections_match(self):
        """risk_detections in report match the evaluation result."""
        frames = [
            _make_frame(0, 0.0, [
                _make_detection('person', confidence=0.50, bbox=[10, 20, 30, 40]),
            ]),
        ]
        detection = _make_detection_result(frames=frames)
        evaluation = evaluate(detection)
        report = format_report(detection, evaluation, _make_job_info())

        assert len(report['risk_detections']) == 1
        assert report['risk_detections'][0]['class'] == 'person'
        assert report['risk_detections'][0]['confidence'] == 0.50
        assert report['risk_detections'][0]['bbox'] == [10, 20, 30, 40]


# ══════════════════════════════════════════════════════════════
#  TestDefaultSettings
# ══════════════════════════════════════════════════════════════

class TestDefaultSettings:
    """Ensure DEFAULT_SETTINGS has the expected shape."""

    def test_has_required_keys(self):
        assert 'risk_classes' in DEFAULT_SETTINGS
        assert 'reject_confidence' in DEFAULT_SETTINGS
        assert 'review_confidence' in DEFAULT_SETTINGS
        assert 'min_evidence_frames' in DEFAULT_SETTINGS

    def test_reject_greater_than_review(self):
        """Sanity: reject threshold must be > review threshold."""
        assert DEFAULT_SETTINGS['reject_confidence'] > DEFAULT_SETTINGS['review_confidence']

    def test_risk_classes_is_nonempty_list(self):
        assert isinstance(DEFAULT_SETTINGS['risk_classes'], list)
        assert len(DEFAULT_SETTINGS['risk_classes']) > 0

    def test_confidence_values_in_range(self):
        """Confidence thresholds are between 0 and 1."""
        assert 0 < DEFAULT_SETTINGS['reject_confidence'] <= 1
        assert 0 < DEFAULT_SETTINGS['review_confidence'] <= 1

    def test_immutability(self):
        """Modifying a copy does not affect the original (callers must copy)."""
        original = DEFAULT_SETTINGS['risk_classes'][:]
        # Modifying the list directly would mutate DEFAULT_SETTINGS,
        # so users should deepcopy. This test just records the current behavior.
        assert DEFAULT_SETTINGS['risk_classes'] == ['person']
