from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user_optional
from app.core.config import load_exercise_config
from app.db.models import SessionModel, UserModel, VideoModel
from app.db.session import get_db
from app.services.jobs import job_manager
from app.services.storage import delete_video_files, save_uploaded_video

router = APIRouter(prefix="/api", tags=["videos"])


class VideoPatchSchema(BaseModel):
    title: str | None = None
    favorite: bool | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ReprocessSchema(BaseModel):
    exercise: str | None = None
    level: str = "medium"


def _serialize_video(video: VideoModel, include_report: bool = False) -> dict[str, Any]:
    latest_session: SessionModel | None = video.sessions[-1] if video.sessions else None
    report_data: dict[str, Any] = {}
    if latest_session and latest_session.report_json:
        try:
            report_data = json.loads(latest_session.report_json)
        except Exception:
            report_data = {}

    tags_list = [t.strip() for t in (video.tags_csv or "").split(",") if t.strip()]

    payload: dict[str, Any] = {
        "id": video.id,
        "title": video.title,
        "exercise": video.exercise,
        "level": video.level,
        "source": video.source,
        "duration_s": round(video.duration_s or 0.0, 2),
        "fps": round(video.fps or 30.0, 1),
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "favorite": bool(video.favorite),
        "notes": video.notes or "",
        "tags": tags_list,
        "status": video.status,
        "has_thumbnail": bool(video.thumbnail_path and Path(video.thumbnail_path).exists()),
        "reps_total": latest_session.reps_total if latest_session else 0,
        "reps_ok": latest_session.reps_ok if latest_session else 0,
        "reps_partial": latest_session.reps_partial if latest_session else 0,
        "reps_bad": latest_session.reps_bad if latest_session else 0,
        "hold_seconds": round(latest_session.hold_seconds, 1) if latest_session else 0.0,
        "score_avg": round(latest_session.score_avg, 1) if latest_session else 0.0,
    }
    if include_report:
        payload["report"] = report_data
    return payload


@router.post("/videos")
def upload_video(
    file: UploadFile = File(...),
    exercise: str = Form("pushup"),
    level: str = Form("medium"),
    title: str | None = Form(None),
    source: str = Form("upload"),
    db: Session = Depends(get_db),
    current_user: UserModel | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Upload a video file, persist metadata in SQLite, and enqueue offline analysis."""
    try:
        ex_cfg = load_exercise_config(exercise)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if level not in ex_cfg.get("levels", {}):
        raise HTTPException(status_code=400, detail=f"Nivel '{level}' no válido")

    video_id = str(uuid.uuid4())
    orig_path = save_uploaded_video(file, video_id)
    ex_display = ex_cfg.get("display_name", exercise.capitalize())
    default_title = title or (file.filename or f"Sesión de {ex_display}")

    video_rec = VideoModel(
        id=video_id,
        user_id=current_user.id if current_user else None,
        title=default_title,
        exercise=exercise,
        level=level,
        source=source,
        original_path=str(orig_path),
        status="queued",
    )
    db.add(video_rec)
    db.commit()

    job = job_manager.create_job(video_id=video_id, exercise=exercise, level=level)
    return {
        "video_id": video_id,
        "job_id": job.job_id,
        "status": job.status,
    }


@router.get("/videos")
def list_videos(
    exercise: str | None = None,
    level: str | None = None,
    favorite: bool | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserModel | None = Depends(get_current_user_optional),
) -> list[dict[str, Any]]:
    """List saved video sessions with optional filtering."""
    query = db.query(VideoModel)
    if current_user is not None:
        query = query.filter(
            (VideoModel.user_id == current_user.id) | (VideoModel.user_id.is_(None))
        )
    if exercise:
        query = query.filter(VideoModel.exercise == exercise)
    if level:
        query = query.filter(VideoModel.level == level)
    if favorite is not None:
        query = query.filter(VideoModel.favorite == favorite)
    if q:
        like_expr = f"%{q.strip()}%"
        query = query.filter(
            (VideoModel.title.ilike(like_expr))
            | (VideoModel.notes.ilike(like_expr))
            | (VideoModel.tags_csv.ilike(like_expr))
        )

    videos = query.order_by(VideoModel.created_at.desc()).all()
    return [_serialize_video(v, include_report=False) for v in videos]


@router.get("/videos/{video_id}")
def get_video_detail(video_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return full metadata and biomechanical report for a single video."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Vídeo no encontrado")
    return _serialize_video(video, include_report=True)


def _range_file_response(file_path: Path, request: Request, media_type: str = "video/mp4"):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichero de vídeo no encontrado en disco")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(path=str(file_path), media_type=media_type)

    try:
        byte_range = range_header.strip().lower().replace("bytes=", "")
        start_str, end_str = byte_range.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        return FileResponse(path=str(file_path), media_type=media_type)

    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))
    chunk_size = (end - start) + 1

    def _file_iterator():
        with file_path.open("rb") as fh:
            fh.seek(start)
            remaining = chunk_size
            while remaining > 0:
                data = fh.read(min(65536, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
    }
    return StreamingResponse(
        _file_iterator(),
        status_code=206,
        media_type=media_type,
        headers=headers,
    )


@router.get("/videos/{video_id}/stream")
def stream_processed_video(
    video_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Stream the processed video with overlay (supports HTTP Range requests)."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Vídeo no encontrado")
    target = video.processed_path or video.original_path
    return _range_file_response(Path(target), request)


@router.get("/videos/{video_id}/original")
def stream_original_video(
    video_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Stream the raw original video for side-by-side comparison."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Vídeo no encontrado")
    return _range_file_response(Path(video.original_path), request)


@router.get("/videos/{video_id}/thumbnail")
def get_video_thumbnail(video_id: str, db: Session = Depends(get_db)):
    """Serve the JPEG thumbnail for a video."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None or not video.thumbnail_path:
        raise HTTPException(status_code=404, detail="Miniatura no disponible")
    thumb_path = Path(video.thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Fichero de miniatura no encontrado")
    return FileResponse(path=str(thumb_path), media_type="image/jpeg")


@router.patch("/videos/{video_id}")
def update_video(
    video_id: str,
    body: VideoPatchSchema,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update title, favorite flag, notes, or tags of a saved video."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Vídeo no encontrado")

    if body.title is not None:
        video.title = body.title.strip() or video.title
    if body.favorite is not None:
        video.favorite = body.favorite
    if body.notes is not None:
        video.notes = body.notes
    if body.tags is not None:
        video.tags_csv = ",".join(t.strip() for t in body.tags if t.strip())

    db.commit()
    db.refresh(video)
    return _serialize_video(video, include_report=True)


@router.delete("/videos/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Delete a video session from SQLite and remove all local files."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Vídeo no encontrado")

    delete_video_files(
        original_path=video.original_path,
        processed_path=video.processed_path,
        thumbnail_path=video.thumbnail_path,
        video_id=video.id,
    )
    db.delete(video)
    db.commit()
    return {"deleted": True, "video_id": video_id}


@router.post("/videos/{video_id}/reprocess")
def reprocess_video(
    video_id: str,
    body: ReprocessSchema,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Reprocess an existing video with a different difficulty level or exercise."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Vídeo no encontrado")

    target_exercise = body.exercise or video.exercise
    try:
        ex_cfg = load_exercise_config(target_exercise)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.level not in ex_cfg.get("levels", {}):
        raise HTTPException(status_code=400, detail=f"Nivel '{body.level}' no válido")

    job = job_manager.create_job(
        video_id=video.id,
        exercise=target_exercise,
        level=body.level,
    )
    return {
        "video_id": video.id,
        "job_id": job.job_id,
        "status": job.status,
    }


@router.get("/stats")
def get_progress_stats(
    db: Session = Depends(get_db),
    current_user: UserModel | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Aggregate historical training statistics for the Progress screen."""
    query = db.query(VideoModel).filter(VideoModel.status == "done")
    if current_user is not None:
        query = query.filter(
            (VideoModel.user_id == current_user.id) | (VideoModel.user_id.is_(None))
        )
    videos = query.order_by(VideoModel.created_at.asc()).all()

    total_sessions = len(videos)
    total_reps = 0
    total_reps_ok = 0
    total_hold_s = 0.0
    scores: list[float] = []
    history: list[dict[str, Any]] = []
    by_exercise: dict[str, dict[str, Any]] = {}
    error_counter: Counter[str] = Counter()
    error_messages: dict[str, str] = {}

    for v in videos:
        s = _serialize_video(v, include_report=True)
        total_reps += s["reps_total"]
        total_reps_ok += s["reps_ok"]
        total_hold_s += s["hold_seconds"]
        if s["score_avg"] > 0:
            scores.append(s["score_avg"])

        history.append(
            {
                "id": s["id"],
                "title": s["title"],
                "date": s["created_at"],
                "exercise": s["exercise"],
                "level": s["level"],
                "score_avg": s["score_avg"],
                "reps_total": s["reps_total"],
                "reps_ok": s["reps_ok"],
                "hold_seconds": s["hold_seconds"],
            }
        )

        ex_key = s["exercise"]
        if ex_key not in by_exercise:
            by_exercise[ex_key] = {
                "exercise": ex_key,
                "sessions": 0,
                "reps_total": 0,
                "best_score": 0.0,
                "max_reps": 0,
            }
        by_exercise[ex_key]["sessions"] += 1
        by_exercise[ex_key]["reps_total"] += s["reps_total"]
        by_exercise[ex_key]["best_score"] = max(by_exercise[ex_key]["best_score"], s["score_avg"])
        by_exercise[ex_key]["max_reps"] = max(by_exercise[ex_key]["max_reps"], s["reps_total"])

        for err in s.get("report", {}).get("top_errors", []):
            rid = err.get("rule_id", "")
            cnt = int(err.get("count", 1))
            if rid:
                error_counter[rid] += cnt
                error_messages[rid] = err.get("message", rid)

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    best_score = round(max(scores), 1) if scores else 0.0

    frequent_errors = [
        {"rule_id": rid, "message": error_messages.get(rid, rid), "count": cnt}
        for rid, cnt in error_counter.most_common(5)
    ]

    return {
        "total_sessions": total_sessions,
        "total_reps": total_reps,
        "total_reps_ok": total_reps_ok,
        "total_hold_seconds": round(total_hold_s, 1),
        "avg_score": avg_score,
        "best_score": best_score,
        "history": history,
        "by_exercise": list(by_exercise.values()),
        "frequent_errors": frequent_errors,
    }
