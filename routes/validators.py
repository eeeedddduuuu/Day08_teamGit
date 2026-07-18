"""
Input validation utilities for API routes.
"""
import re
import os


# Valid file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'mp4', 'avi', 'mov', 'webm'}

# Valid review verdicts
VALID_VERDICTS = {'pass', 'review', 'reject'}

# job_id pattern: YYYYMMDD_HHMMSS_8hex
JOB_ID_PATTERN = re.compile(r'^\d{8}_\d{6}_[0-9a-f]{8}$')


def validate_job_id(job_id: str) -> bool:
    """Validate job_id format: YYYYMMDD_HHMMSS_8hex."""
    if not isinstance(job_id, str):
        return False
    return bool(JOB_ID_PATTERN.match(job_id))


def validate_file_extension(filename: str) -> bool:
    """Check file extension against whitelist."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_not_empty(file_size: int) -> bool:
    """Check file is not empty (0 bytes)."""
    return file_size > 0


def validate_verdict(verdict: str) -> bool:
    """Check verdict is one of: pass, review, reject."""
    return verdict in VALID_VERDICTS


def validate_job_not_running(job: dict) -> bool:
    """Check job status is safe to delete (not queued or running)."""
    return job.get('status') not in ('queued', 'running')
