"""
Job CRUD API Routes

Public endpoints:
  GET    /api/health
  POST   /api/jobs
  GET    /api/jobs
  GET    /api/jobs/<job_id>
  DELETE /api/jobs/<job_id>
"""
import os
import json
import uuid
import shutil
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app

from routes.validators import (
    validate_job_id,
    validate_file_extension,
    validate_file_not_empty,
    validate_job_not_running,
)
from services import load_job, save_job

jobs_bp = Blueprint('jobs', __name__)

STATES = ['created', 'queued', 'running', 'completed', 'failed']

VALID_TRANSITIONS = {
    'created':   ['queued'],
    'queued':    ['running', 'failed'],
    'running':   ['completed', 'failed'],
    'completed': [],
    'failed':    ['queued'],
}


def _generate_job_id() -> str:
    """Generate unique job ID: YYYYMMDD_HHMMSS_8hex"""
    now = datetime.now()
    hex_part = uuid.uuid4().hex[:8]
    return now.strftime(f'%Y%m%d_%H%M%S_{hex_part}')


def _job_dir(job_id: str) -> str:
    """Get job directory path."""
    return os.path.join(current_app.config['OUTPUTS_DIR'], job_id)


def _job_json_path(job_id: str) -> str:
    """Get job.json path."""
    return os.path.join(_job_dir(job_id), 'job.json')


def _transition_status(job_id: str, new_status: str) -> dict:
    """Transition a job to a new status and persist."""
    job_path = _job_json_path(job_id)
    job = load_job(job_path)

    current_status = job.get('status', 'created')
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise ValueError(
            f'无效的状态转换: {current_status} -> {new_status}'
        )

    job['status'] = new_status
    now = datetime.now().isoformat()

    if new_status == 'running':
        job['started_at'] = now
    elif new_status in ('completed', 'failed'):
        job['completed_at'] = now

    save_job(job_path, job)
    return job


def _run_analysis_async(job_id: str):
    """
    Background analysis thread.
    Updates status -> running -> completed/failed.
    """
    try:
        _transition_status(job_id, 'running')

        # Deferred import to avoid circular dependency
        from services.detector import detect
        from services.review_engine import evaluate

        job_dir = _job_dir(job_id)
        input_dir = os.path.join(job_dir, 'input')
        # Find the uploaded file in input/
        input_files = os.listdir(input_dir)
        if not input_files:
            raise FileNotFoundError('输入目录中没有找到文件')
        file_path = os.path.join(input_dir, input_files[0])

        # Run YOLO detection
        detection_result = detect(file_path, job_dir)

        # Load settings from job.json
        job = load_job(_job_json_path(job_id))
        settings = job.get('settings', None)

        # Run review engine
        evaluation_result = evaluate(detection_result, settings)

        # Build final report
        from services.review_engine import format_report
        report = format_report(detection_result, evaluation_result, job)

        # Write analysis report
        result_dir = os.path.join(job_dir, 'result')
        os.makedirs(result_dir, exist_ok=True)
        report_path = os.path.join(result_dir, 'analysis_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # Also write at job root level for easy access
        root_report_path = os.path.join(job_dir, 'analysis_report.json')
        with open(root_report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        _transition_status(job_id, 'completed')

    except Exception as e:
        import traceback
        # Persist failed status with error
        job_path = _job_json_path(job_id)
        job = load_job(job_path)
        job['status'] = 'failed'
        job['completed_at'] = datetime.now().isoformat()
        job['error'] = traceback.format_exc()
        save_job(job_path, job)


# ──────────────────────────────────────────────
#  GET /api/health
# ──────────────────────────────────────────────
@jobs_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    model_path = current_app.config['MODEL_PATH']
    model_ready = os.path.exists(model_path)

    return jsonify({
        'status': 'ok',
        'model_ready': model_ready,
        'direction': 'A',
    })


# ──────────────────────────────────────────────
#  POST /api/jobs
# ──────────────────────────────────────────────
@jobs_bp.route('/jobs', methods=['POST'])
def create_job():
    """
    Create a new job with uploaded file.
    Request: multipart/form-data
      - file: uploaded file
      - project_name: string
    """
    try:
        # Validate file presence
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': '缺少上传文件'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'ok': False, 'error': '文件名为空'}), 400

        # Validate project_name
        project_name = request.form.get('project_name', '').strip()
        if not project_name:
            return jsonify({'ok': False, 'error': '缺少项目名称'}), 400

        # Validate file extension
        if not validate_file_extension(file.filename):
            return jsonify({
                'ok': False,
                'error': f'不支持的文件格式: {file.filename.rsplit(".", 1)[-1] if "." in file.filename else "未知"}。支持: jpg, jpeg, png, mp4, avi, mov, webm'
            }), 400

        # Validate file is not empty
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if not validate_file_not_empty(file_size):
            return jsonify({'ok': False, 'error': '文件为空'}), 400

        if file_size > 500 * 1024 * 1024:
            return jsonify({'ok': False, 'error': '文件大小超过 500MB 限制'}), 400

        # Create job
        job_id = _generate_job_id()
        job_dir = _job_dir(job_id)
        input_dir = os.path.join(job_dir, 'input')
        os.makedirs(input_dir, exist_ok=True)

        # Save uploaded file
        safe_filename = Path(file.filename).name
        file_path = os.path.join(input_dir, safe_filename)
        file.save(file_path)

        # Determine asset name
        asset_name = safe_filename

        # Write job.json
        now = datetime.now().isoformat()
        job = {
            'job_id': job_id,
            'project_name': project_name,
            'asset_name': asset_name,
            'status': 'created',
            'created_at': now,
            'started_at': None,
            'completed_at': None,
            'settings': {
                'risk_classes': ['person'],
                'reject_confidence': 0.60,
                'review_confidence': 0.35,
                'min_evidence_frames': 1,
            },
            'result_file': 'analysis_report.json',
            'error': None,
        }
        save_job(_job_json_path(job_id), job)

        # Transition to queued and start analysis in background
        _transition_status(job_id, 'queued')
        thread = threading.Thread(target=_run_analysis_async, args=(job_id,), daemon=True)
        thread.start()

        return jsonify({'ok': True, 'job_id': job_id}), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500


# ──────────────────────────────────────────────
#  GET /api/jobs
# ──────────────────────────────────────────────
@jobs_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs, ordered by created_at descending."""
    try:
        outputs_dir = current_app.config['OUTPUTS_DIR']
        jobs = []

        if os.path.exists(outputs_dir):
            for dir_name in os.listdir(outputs_dir):
                job_json_path = os.path.join(outputs_dir, dir_name, 'job.json')
                if os.path.exists(job_json_path):
                    job = load_job(job_json_path)
                    jobs.append({
                        'job_id': job.get('job_id'),
                        'project_name': job.get('project_name'),
                        'asset_name': job.get('asset_name'),
                        'status': job.get('status'),
                        'created_at': job.get('created_at'),
                    })

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.get('created_at', ''), reverse=True)

        return jsonify({'ok': True, 'jobs': jobs})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500


# ──────────────────────────────────────────────
#  GET /api/jobs/<job_id>
# ──────────────────────────────────────────────
@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get single job full details."""
    try:
        if not validate_job_id(job_id):
            return jsonify({'ok': False, 'error': '无效的任务编号格式'}), 400

        job_path = _job_json_path(job_id)
        if not os.path.exists(job_path):
            return jsonify({'ok': False, 'error': '任务不存在'}), 404

        job = load_job(job_path)

        # Attempt to load report if exists
        report = None
        report_path = os.path.join(_job_dir(job_id), 'analysis_report.json')
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

        return jsonify({'ok': True, 'job': job, 'report': report})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500


# ──────────────────────────────────────────────
#  DELETE /api/jobs/<job_id>
# ──────────────────────────────────────────────
@jobs_bp.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job and all its files."""
    try:
        if not validate_job_id(job_id):
            return jsonify({'ok': False, 'error': '无效的任务编号格式'}), 400

        job_path = _job_json_path(job_id)
        if not os.path.exists(job_path):
            return jsonify({'ok': False, 'error': '任务不存在'}), 404

        job = load_job(job_path)

        if not validate_job_not_running(job):
            return jsonify({
                'ok': False,
                'error': f'任务状态为 {job["status"]}，无法删除。只能删除已完成或失败的任务'
            }), 409

        # Delete entire job directory
        job_dir = _job_dir(job_id)
        shutil.rmtree(job_dir)

        return jsonify({'ok': True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'服务器内部错误: {str(e)}'}), 500
