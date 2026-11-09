from __future__ import annotations

import math

import numpy as np

from app.core.config import CONFIDENCE_THRESHOLD
from app.core.pose.base import Person


class OneEuroFilter1D:
    """1D One-Euro filter for low-latency signal smoothing."""

    def __init__(
        self,
        min_cutoff: float = 1.2,
        beta: float = 0.015,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev: float | None = None
        self._dx_prev: float = 0.0
        self._t_prev: float | None = None

    @staticmethod
    def _smoothing_factor(t_e: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * t_e
        return r / (r + 1.0)

    def reset(self) -> None:
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    def __call__(self, x: float, t: float) -> float:
        if self._x_prev is None or self._t_prev is None:
            self._x_prev = x
            self._t_prev = t
            return x

        t_e = t - self._t_prev
        if t_e <= 1e-6:
            return self._x_prev

        a_d = self._smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self._x_prev) / t_e
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x + (1.0 - a) * self._x_prev

        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t
        return x_hat


class KeypointSmoother:
    """
    Applies 2D One-Euro filtering to all 17 COCO keypoints of a person
    and interpolates short confidence drops up to `max_missing_frames`.
    """

    def __init__(
        self,
        min_cutoff: float = 1.4,
        beta: float = 0.02,
        d_cutoff: float = 1.0,
        conf_threshold: float = CONFIDENCE_THRESHOLD,
        max_missing_frames: int = 5,
    ) -> None:
        self.conf_threshold = conf_threshold
        self.max_missing_frames = max_missing_frames
        self._filters_x = [OneEuroFilter1D(min_cutoff, beta, d_cutoff) for _ in range(17)]
        self._filters_y = [OneEuroFilter1D(min_cutoff, beta, d_cutoff) for _ in range(17)]
        self._last_valid_xy = np.zeros((17, 2), dtype=np.float32)
        self._has_valid = np.zeros(17, dtype=bool)
        self._missing_count = np.zeros(17, dtype=np.int32)

    def reset(self) -> None:
        for fx, fy in zip(self._filters_x, self._filters_y):
            fx.reset()
            fy.reset()
        self._has_valid.fill(False)
        self._missing_count.fill(0)

    def smooth(self, person: Person, timestamp: float) -> Person:
        smoothed_xy = np.copy(person.keypoints)
        smoothed_conf = np.copy(person.confidences)

        for i in range(17):
            conf = float(person.confidences[i])
            raw_x, raw_y = float(person.keypoints[i, 0]), float(person.keypoints[i, 1])

            if conf >= self.conf_threshold:
                sx = self._filters_x[i](raw_x, timestamp)
                sy = self._filters_y[i](raw_y, timestamp)
                smoothed_xy[i, 0] = sx
                smoothed_xy[i, 1] = sy
                self._last_valid_xy[i] = (sx, sy)
                self._has_valid[i] = True
                self._missing_count[i] = 0
            elif self._has_valid[i] and self._missing_count[i] < self.max_missing_frames:
                # Short occlusion: hold last smoothed coordinate with decayed confidence
                self._missing_count[i] += 1
                smoothed_xy[i] = self._last_valid_xy[i]
                smoothed_conf[i] = max(0.35, conf)
            else:
                self._missing_count[i] += 1

        return Person(
            keypoints=smoothed_xy,
            confidences=smoothed_conf,
            bbox=person.bbox,
            track_id=person.track_id,
        )
