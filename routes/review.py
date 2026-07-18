"""
Direction A — Review API Routes

  POST   /api/jobs/<job_id>/analyze
  PATCH  /api/jobs/<job_id>/review
  GET    /api/jobs/<job_id>/report
"""
import os
import json
import threading
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

from routes.validators import validate_job_id, validate_verdict
from services import load_job, save_job

review_bp = Blueprint('review', __name__)


def _job_dir(job_id: str) -> str:
    return os.path.join(current_app.config['OUTPUTS_DIR'], job_id)


def _job_json_path(job_id: str) -> str:
    return os.path.join(_job_dir(job_id), 'job.json')


def _report_path(job_id: str) -> str:
    return os.path.join(_job_dir(job_id), 'analysis_report.json')


# ──────────────────────────────────────────────
#  POST /api/jobs/<job_id>/analyze
# ──────────────────────────────────────────────
@review_bp.route('/jobs/<job_id>/analyze', methods=['POST'])
def analyze_job(job_id):
    """Trigger (or re-trigger) analysis for a job."""
    try:
        if not validate_job_id(job_id):
            return jsonify({'ok': False, 'error': '无效的任务编号格式'}), 400

        job_path = _job_json_path(job_id)
        if not os.path.exists(job_path):
            return jsonify({'ok': False, 'error': '任务不存在'}), 404

        job = load_job(job_path)

        # Verify input file exists
        input_dir = os.path.join(_job_dir(job_id), 'input')
        if not os.path.exists(input_dir) or not os.listdir(input_dir):
            return jsonify({'ok': False, 'error': '输入文件不存在'}), 400

        # Set status to queued
        job['status'] = 'queued'
        save_job(job_path, job)

        # Start background analysis
        from routes.jobs import _run_analysis_async
        thread = threading.Thread(target=_run_analysis_async, args=(job_id,), daemon=True)
        thread.start()

        return jsonify({'ok': True, 'job_id': job_id, 'status': 'queued'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500


# ──────────────────────────────────────────────
#  PATCH /api/jobs/<job_id>/review
# ──────────────────────────────────────────────
@review_bp.route('/jobs/<job_id>/review', methods=['PATCH'])
def review_job(job_id):
    """Manual review — update verdict with reviewer info."""
    try:
        if not validate_job_id(job_id):
            return jsonify({'ok': False, 'error': '无效的任务编号格式'}), 400

        job_path = _job_json_path(job_id)
        if not os.path.exists(job_path):
            return jsonify({'ok': False, 'error': '任务不存在'}), 404

        job = load_job(job_path)

        if job.get('status') != 'completed':
            return jsonify({
                'ok': False,
                'error': f'任务状态为 {job.get("status")}，只有已完成的任务才能进行人工审核'
            }), 409

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'ok': False, 'error': '请求体不能为空'}), 400

        verdict = data.get('verdict')
        if not validate_verdict(verdict):
            return jsonify({
                'ok': False,
                'error': f'无效的审核结论: {verdict}，必须是 pass / review / reject'
            }), 400

        # Load report and update manual_review
        rp = _report_path(job_id)
        if not os.path.exists(rp):
            return jsonify({'ok': False, 'error': '分析报告不存在，请先执行分析'}), 404

        with open(rp, 'r', encoding='utf-8') as f:
            report = json.load(f)

        report['manual_review'] = {
            'verdict': verdict,
            'reviewer': data.get('reviewer', ''),
            'notes': data.get('notes', ''),
            'reviewed_at': datetime.now().isoformat(),
        }

        with open(rp, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Also sync to result dir copy
        result_report = os.path.join(_job_dir(job_id), 'result', 'analysis_report.json')
        if os.path.exists(os.path.dirname(result_report)):
            with open(result_report, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return jsonify({'ok': True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500


# ──────────────────────────────────────────────
#  GET /api/jobs/<job_id>/report
# ──────────────────────────────────────────────
@review_bp.route('/jobs/<job_id>/report', methods=['GET'])
def get_report(job_id):
    """Get analysis report for a job."""
    try:
        if not validate_job_id(job_id):
            return jsonify({'ok': False, 'error': '无效的任务编号格式'}), 400

        rp = _report_path(job_id)
        if not os.path.exists(rp):
            return jsonify({'ok': False, 'error': '分析报告不存在'}), 404

        with open(rp, 'r', encoding='utf-8') as f:
            report = json.load(f)

        return jsonify({'ok': True, 'report': report})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500
