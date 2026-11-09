from __future__ import annotations

import base64
import json
import logging
import time

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.exercises import create_analyzer
from app.core.pose.yolo_pose import YoloPoseEstimator
from app.core.smoothing import KeypointSmoother
from app.core.tracking import PersonTracker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live"])

# Shared estimator instance for low-latency live sessions
_shared_estimator: YoloPoseEstimator | None = None


def _get_live_estimator() -> YoloPoseEstimator:
    global _shared_estimator
    if _shared_estimator is None:
        _shared_estimator = YoloPoseEstimator(imgsz=640, conf=0.30)
    return _shared_estimator


@router.websocket("/ws/live")
async def websocket_live_session(
    websocket: WebSocket,
    exercise: str = "pushup",
    level: str = "medium",
) -> None:
    """
    Real-time WebSocket endpoint for live training:
    Receives JSON messages containing base64 JPEG frames (`{"frame": "data:image/jpeg;base64,..."}`)
    or binary JPEG bytes, runs pose estimation + smoothing + biomechanical analysis,
    and replies with JSON containing keypoints, joint states, angles, rep counts, and feedback.
    """
    await websocket.accept()
    try:
        analyzer = create_analyzer(exercise=exercise, level=level)
    except ValueError as exc:
        await websocket.send_json({"error": str(exc)})
        await websocket.close()
        return

    tracker = PersonTracker()
    smoother = KeypointSmoother()
    estimator = _get_live_estimator()
    session_start = time.monotonic()

    try:
        while True:
            message = await websocket.receive()
            if message.get("text"):
                raw_text = message["text"]
                try:
                    data = json.loads(raw_text)
                except json.JSONDecodeError:
                    continue

                if data.get("type") == "reset":
                    analyzer.reset()
                    tracker.reset()
                    smoother.reset()
                    session_start = time.monotonic()
                    await websocket.send_json({"type": "reset_ack"})
                    continue

                if data.get("type") == "summary":
                    await websocket.send_json(
                        {
                            "type": "summary",
                            "summary": analyzer.summarize().to_dict(),
                        }
                    )
                    continue

                frame_b64 = data.get("frame", "")
                if not frame_b64:
                    continue
                if "," in frame_b64:
                    frame_b64 = frame_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(frame_b64)
                timestamp = float(data.get("timestamp", time.monotonic() - session_start))
            elif message.get("bytes"):
                img_bytes = message["bytes"]
                timestamp = time.monotonic() - session_start
            else:
                break

            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame_bgr is None:
                continue

            h, w = frame_bgr.shape[:2]
            persons = estimator.infer(frame_bgr, track=True)
            main_person = tracker.select(persons, w, h)
            if main_person is not None:
                main_person = smoother.smooth(main_person, timestamp)

            analysis = analyzer.analyze_frame(
                main_person,
                timestamp=timestamp,
                frame_width=w,
                frame_height=h,
            )

            keypoints_payload = []
            if main_person is not None:
                for idx in range(17):
                    keypoints_payload.append(
                        {
                            "index": idx,
                            "x": round(
                                float(main_person.keypoints[idx, 0]) / max(1.0, float(w)), 4
                            ),
                            "y": round(
                                float(main_person.keypoints[idx, 1]) / max(1.0, float(h)), 4
                            ),
                            "conf": round(float(main_person.confidences[idx]), 3),
                            "state": analysis.joint_states.get(idx, "ok"),
                        }
                    )

            ideal_line_norm = None
            if analysis.ideal_line is not None:
                (x1, y1), (x2, y2) = analysis.ideal_line
                ideal_line_norm = [
                    {
                        "x": round(x1 / max(1.0, float(w)), 4),
                        "y": round(y1 / max(1.0, float(h)), 4),
                    },
                    {
                        "x": round(x2 / max(1.0, float(w)), 4),
                        "y": round(y2 / max(1.0, float(h)), 4),
                    },
                ]

            resp = analysis.to_dict()
            resp["type"] = "frame_analysis"
            resp["keypoints"] = keypoints_payload
            resp["ideal_line_norm"] = ideal_line_norm
            await websocket.send_json(resp)

    except WebSocketDisconnect:
        logger.info("Cliente desconectado de /ws/live")
    except Exception as exc:
        logger.warning("Excepción en /ws/live: %s", exc)
