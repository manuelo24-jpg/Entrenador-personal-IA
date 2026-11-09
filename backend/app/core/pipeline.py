from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import cv2

from app.core.config import load_exercise_config
from app.core.exercises import create_analyzer
from app.core.pose.base import PoseEstimator
from app.core.pose.yolo_pose import YoloPoseEstimator
from app.core.render import OverlayRenderer
from app.core.scoring import SessionSummary
from app.core.smoothing import KeypointSmoother
from app.core.tracking import PersonTracker
from app.services.ffmpeg import generate_thumbnail, transcode_to_h264


def process_video_pipeline(
    input_video_path: Path,
    output_video_path: Path,
    exercise: str,
    level: str = "medium",
    thumbnail_path: Path | None = None,
    report_json_path: Path | None = None,
    pose_estimator: PoseEstimator | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[SessionSummary, float, float]:
    """
    Process a complete video offline:
      1. Decode frames -> YOLO11-pose -> PersonTracker -> KeypointSmoother
      2. Run ExerciseAnalyzer per frame
      3. Render Unicode overlay (skeleton, angles, HUD, feedback)
      4. Append 2.5s summary card at the end
      5. Transcode to H.264 MP4 via FFmpeg + generate thumbnail & JSON report
    Returns: (session_summary, duration_seconds, fps)
    """
    if not input_video_path.exists():
        raise FileNotFoundError(f"Vídeo de entrada no encontrado: {input_video_path}")

    cap = cv2.VideoCapture(str(input_video_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el vídeo: {input_video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if fps <= 1.0 or fps > 120.0:
        fps = 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    ex_cfg = load_exercise_config(exercise)
    ex_display = str(ex_cfg.get("display_name", exercise.capitalize()))
    lvl_display = str(
        ex_cfg.get("levels", {}).get(level, {}).get("display_name", level.capitalize())
    )
    is_iso = bool(ex_cfg.get("is_isometric", False))

    estimator = pose_estimator or YoloPoseEstimator()
    tracker = PersonTracker()
    smoother = KeypointSmoother()
    analyzer = create_analyzer(exercise=exercise, level=level)
    renderer = OverlayRenderer(
        exercise_display=ex_display,
        level_display=lvl_display,
        is_isometric=is_iso,
    )

    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    temp_raw_path = output_video_path.with_suffix(".raw.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(temp_raw_path), fourcc, fps, (width, height))

    frame_idx = 0
    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok or frame_bgr is None:
                break

            timestamp = frame_idx / fps
            persons = estimator.infer(frame_bgr, track=True)
            main_person = tracker.select(persons, width, height)
            if main_person is not None:
                main_person = smoother.smooth(main_person, timestamp)

            analysis = analyzer.analyze_frame(
                main_person,
                timestamp=timestamp,
                frame_width=width,
                frame_height=height,
            )
            annotated = renderer.render_frame(frame_bgr, main_person, analysis)
            writer.write(annotated)

            frame_idx += 1
            if progress_callback and total_frames > 0:
                progress_callback(frame_idx, total_frames)

        summary = analyzer.summarize()

        # Append summary card for ~2.5 seconds at the end of the video
        summary_frame = renderer.render_summary_card(width, height, summary)
        summary_frames_count = max(1, int(round(fps * 2.5)))
        for _ in range(summary_frames_count):
            writer.write(summary_frame)

    finally:
        cap.release()
        writer.release()

    duration_s = round(frame_idx / fps, 2)

    # Transcode to browser-ready H.264 MP4 and clean up temporary raw file
    transcode_to_h264(
        raw_video_path=temp_raw_path,
        output_video_path=output_video_path,
        original_audio_source=input_video_path,
    )
    if temp_raw_path.exists() and temp_raw_path != output_video_path:
        try:
            temp_raw_path.unlink()
        except OSError:
            pass

    if thumbnail_path is not None:
        generate_thumbnail(output_video_path, thumbnail_path)

    if report_json_path is not None:
        report_json_path.parent.mkdir(parents=True, exist_ok=True)
        with report_json_path.open("w", encoding="utf-8") as fh:
            json.dump(summary.to_dict(), fh, ensure_ascii=False, indent=2)

    return summary, duration_s, fps
