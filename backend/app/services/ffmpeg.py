from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)


def get_ffmpeg_binary() -> str | None:
    """Locate FFmpeg executable on PATH or via `imageio-ffmpeg`."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def transcode_to_h264(
    raw_video_path: Path,
    output_video_path: Path,
    original_audio_source: Path | None = None,
) -> bool:
    """
    Transcode a raw video file to browser-playable MP4 (H.264 + yuv420p + faststart),
    optionally merging audio from `original_audio_source`.
    Falls back to copying `raw_video_path` if FFmpeg is unavailable.
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_binary()
    if not ffmpeg_bin:
        logger.warning("FFmpeg no encontrado; usando vídeo directo de OpenCV.")
        shutil.copyfile(raw_video_path, output_video_path)
        return False

    cmd: list[str] = [ffmpeg_bin, "-y", "-i", str(raw_video_path)]
    if original_audio_source and original_audio_source.exists():
        cmd.extend(["-i", str(original_audio_source)])
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0?"])
    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_video_path),
        ]
    )

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
        if res.returncode == 0 and output_video_path.exists():
            return True
        logger.warning("FFmpeg retornó código %s: %s", res.returncode, res.stderr[:300])
    except Exception as exc:
        logger.warning("Fallo al ejecutar FFmpeg: %s", exc)

    shutil.copyfile(raw_video_path, output_video_path)
    return False


def generate_thumbnail(video_path: Path, thumbnail_path: Path, max_width: int = 480) -> bool:
    """Extract a representative frame from `video_path` and save as a JPEG thumbnail."""
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        target_frame = max(0, min(total_frames // 3, 30)) if total_frames > 0 else 0
        if target_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok or frame is None:
            return False

        h, w = frame.shape[:2]
        if w > max_width:
            new_h = max(1, int(round(h * (max_width / float(w)))))
            frame = cv2.resize(frame, (max_width, new_h), interpolation=cv2.INTER_AREA)

        cv2.imwrite(str(thumbnail_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return thumbnail_path.exists()
    finally:
        cap.release()
