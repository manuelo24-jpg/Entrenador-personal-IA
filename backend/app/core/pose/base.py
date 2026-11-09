from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

# COCO 17 Keypoint indices
COCO_KEYPOINTS: dict[str, int] = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
}

SIDE_JOINT_MAP: dict[str, dict[str, int]] = {
    "left": {
        "ear": 3,
        "shoulder": 5,
        "elbow": 7,
        "wrist": 9,
        "hip": 11,
        "knee": 13,
        "ankle": 15,
    },
    "right": {
        "ear": 4,
        "shoulder": 6,
        "elbow": 8,
        "wrist": 10,
        "hip": 12,
        "knee": 14,
        "ankle": 16,
    },
}

SKELETON_EDGES: list[tuple[int, int]] = [
    (5, 6),  # shoulders
    (5, 7),  # left upper arm
    (7, 9),  # left forearm
    (6, 8),  # right upper arm
    (8, 10),  # right forearm
    (5, 11),  # left torso
    (6, 12),  # right torso
    (11, 12),  # hips
    (11, 13),  # left thigh
    (13, 15),  # left lower leg
    (12, 14),  # right thigh
    (14, 16),  # right lower leg
]


@dataclass
class Person:
    """Detected person with 17 COCO keypoints in pixel coordinates."""

    keypoints: np.ndarray  # shape (17, 2) float32 [x, y]
    confidences: np.ndarray  # shape (17,) float32 [0..1]
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    track_id: int | None = None

    def get_joint(self, side: str, joint_name: str) -> tuple[np.ndarray, float]:
        """Return (xy, confidence) for a named joint on 'left' or 'right' side."""
        idx = SIDE_JOINT_MAP[side][joint_name]
        return self.keypoints[idx], float(self.confidences[idx])

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class PoseEstimator(Protocol):
    """Protocol for interchangeable pose estimation engines (YOLO11, MediaPipe, RTMPose)."""

    def infer(self, frame_bgr: np.ndarray, track: bool = True) -> list[Person]:
        """Run pose estimation on a BGR frame and return detected persons."""
        ...
