"""Services layer — business logic and utility functions."""

import json
import os


def load_job(job_path: str) -> dict:
    """Load job.json from disk. Returns empty dict if not found."""
    if not os.path.exists(job_path):
        return {}
    with open(job_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_job(job_path: str, job: dict) -> None:
    """Save job dict to disk as JSON."""
    os.makedirs(os.path.dirname(job_path), exist_ok=True)
    with open(job_path, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=2)
