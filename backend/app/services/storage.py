from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile

from app.core.config import (
    REPORTS_DIR,
    THUMBNAILS_DIR,
    VIDEOS_ORIG_DIR,
    VIDEOS_PROC_DIR,
    ensure_data_dirs,
)


def save_uploaded_video(upload_file: UploadFile, video_id: str) -> Path:
    """Persist an uploaded video file to `data/videos/original/<video_id><ext>`."""
    ensure_data_dirs()
    suffix = Path(upload_file.filename or "video.mp4").suffix.lower()
    if suffix not in {".mp4", ".webm", ".mov", ".avi", ".mkv"}:
        suffix = ".mp4"
    dest_path = VIDEOS_ORIG_DIR / f"{video_id}{suffix}"
    with dest_path.open("wb") as out_fh:
        shutil.copyfileobj(upload_file.file, out_fh)
    return dest_path


def get_video_paths(video_id: str) -> tuple[Path, Path, Path]:
    """Return (processed_video_path, thumbnail_path, report_json_path) for `video_id`."""
    ensure_data_dirs()
    proc_path = VIDEOS_PROC_DIR / f"{video_id}_epia.mp4"
    thumb_path = THUMBNAILS_DIR / f"{video_id}.jpg"
    report_path = REPORTS_DIR / f"{video_id}.json"
    return proc_path, thumb_path, report_path


def delete_video_files(
    original_path: str | None,
    processed_path: str | None,
    thumbnail_path: str | None,
    video_id: str | None = None,
) -> None:
    """Safely remove all disk artifacts associated with a video session."""
    paths_to_remove: list[Path] = []
    for p_str in (original_path, processed_path, thumbnail_path):
        if p_str:
            paths_to_remove.append(Path(p_str))
    if video_id:
        paths_to_remove.append(REPORTS_DIR / f"{video_id}.json")

    for path in paths_to_remove:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
