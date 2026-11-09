from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.jobs import job_manager

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Query status and progress percentage of a video processing job."""
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Trabajo de procesado no encontrado")
    return job.to_dict()
