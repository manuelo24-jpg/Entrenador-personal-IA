from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.pipeline import process_video_pipeline
from app.db.models import RepModel, SessionModel, VideoModel
from app.db.session import SessionLocal
from app.services.storage import get_video_paths

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    job_id: str
    video_id: str
    exercise: str
    level: str
    status: str = "queued"  # "queued" | "processing" | "done" | "error"
    progress: int = 0  # 0..100
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "video_id": self.video_id,
            "exercise": self.exercise,
            "level": self.level,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
        }


class JobManager:
    """Thread-safe background job queue for video analysis."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def create_job(self, video_id: str, exercise: str, level: str) -> JobState:
        job_id = str(uuid.uuid4())
        state = JobState(
            job_id=job_id,
            video_id=video_id,
            exercise=exercise,
            level=level,
            status="queued",
            progress=0,
        )
        with self._lock:
            self._jobs[job_id] = state

        worker = threading.Thread(
            target=self._run_job,
            args=(job_id,),
            daemon=True,
        )
        worker.start()
        return state

    def get_job(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        if job is None:
            return

        job.status = "processing"
        job.progress = 5

        db = SessionLocal()
        try:
            video = db.query(VideoModel).filter(VideoModel.id == job.video_id).first()
            if video is None:
                job.status = "error"
                job.error_message = "Vídeo no encontrado en la base de datos"
                return

            video.status = "processing"
            video.exercise = job.exercise
            video.level = job.level
            db.commit()

            orig_path = Path(video.original_path)
            proc_path, thumb_path, report_path = get_video_paths(video.id)

            def _on_progress(current_frame: int, total_frames: int) -> None:
                if total_frames > 0:
                    pct = int(round((current_frame / float(total_frames)) * 88.0))
                    job.progress = max(5, min(93, 5 + pct))

            summary, duration_s, fps = process_video_pipeline(
                input_video_path=orig_path,
                output_video_path=proc_path,
                exercise=job.exercise,
                level=job.level,
                thumbnail_path=thumb_path,
                report_json_path=report_path,
                progress_callback=_on_progress,
            )

            # Remove previous session records for this video if reprocessing
            db.query(SessionModel).filter(SessionModel.video_id == video.id).delete()

            session_id = str(uuid.uuid4())
            session_rec = SessionModel(
                id=session_id,
                video_id=video.id,
                reps_total=summary.reps_total,
                reps_ok=summary.reps_ok,
                reps_partial=summary.reps_partial,
                reps_bad=summary.reps_bad,
                hold_seconds=summary.hold_seconds,
                score_avg=summary.score_avg,
                report_json=json.dumps(summary.to_dict(), ensure_ascii=False),
            )
            db.add(session_rec)

            for rep in summary.reps:
                db.add(
                    RepModel(
                        session_id=session_id,
                        index=rep.index,
                        start_t=rep.start_t,
                        end_t=rep.end_t,
                        min_angle=rep.min_angle,
                        max_angle=rep.max_angle,
                        score=rep.score,
                        status=rep.status,
                        errors_json=json.dumps(rep.errors, ensure_ascii=False),
                    )
                )

            video.processed_path = str(proc_path)
            video.thumbnail_path = str(thumb_path) if thumb_path.exists() else None
            video.duration_s = duration_s
            video.fps = fps
            video.status = "done"
            db.commit()

            job.progress = 100
            job.status = "done"

        except Exception as exc:
            logger.exception("Error procesando job %s: %s", job_id, exc)
            job.status = "error"
            job.error_message = str(exc)
            try:
                video = db.query(VideoModel).filter(VideoModel.id == job.video_id).first()
                if video:
                    video.status = "error"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()


job_manager = JobManager()
