from __future__ import annotations

import logging

import numpy as np

from app.core.config import DEFAULT_POSE_MODEL, MODELS_DIR
from app.core.pose.base import Person

logger = logging.getLogger(__name__)


class YoloPoseEstimator:
    """YOLO11-pose estimator implementing PoseEstimator."""

    def __init__(
        self,
        model_name: str = DEFAULT_POSE_MODEL,
        imgsz: int = 640,
        conf: float = 0.30,
    ) -> None:
        self.model_name = model_name
        self.imgsz = imgsz
        self.conf = conf
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO

            local_path = MODELS_DIR / self.model_name
            target = str(local_path) if local_path.exists() else self.model_name
            logger.info("Cargando modelo YOLO11-pose desde %s", target)
            self._model = YOLO(target)
        except Exception as exc:
            logger.warning(
                "Ultralytics YOLO no disponible (%s). Usando estimador de respaldo.",
                exc,
            )
            self._model = False
        return self._model

    def infer(self, frame_bgr: np.ndarray, track: bool = True) -> list[Person]:
        model = self._load_model()
        if not model:
            return []
        if track:
            try:
                results = model.track(
                    frame_bgr,
                    imgsz=self.imgsz,
                    conf=self.conf,
                    persist=True,
                    verbose=False,
                )
            except Exception:
                results = model.predict(
                    frame_bgr,
                    imgsz=self.imgsz,
                    conf=self.conf,
                    verbose=False,
                )
        else:
            results = model.predict(
                frame_bgr,
                imgsz=self.imgsz,
                conf=self.conf,
                verbose=False,
            )

        persons: list[Person] = []
        if not results:
            return persons

        res = results[0]
        if res.keypoints is None or res.boxes is None:
            return persons

        kpts_xy = res.keypoints.xy.cpu().numpy()
        kpts_conf = (
            res.keypoints.conf.cpu().numpy()
            if res.keypoints.conf is not None
            else np.ones((len(kpts_xy), 17), dtype=np.float32)
        )
        boxes_xyxy = res.boxes.xyxy.cpu().numpy()
        track_ids = (
            res.boxes.id.int().cpu().tolist()
            if res.boxes.id is not None
            else [None] * len(boxes_xyxy)
        )

        for i in range(len(kpts_xy)):
            if kpts_xy[i].shape[0] < 17:
                continue
            bx = boxes_xyxy[i]
            persons.append(
                Person(
                    keypoints=kpts_xy[i].astype(np.float32),
                    confidences=kpts_conf[i].astype(np.float32),
                    bbox=(float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])),
                    track_id=track_ids[i],
                )
            )

        return persons
