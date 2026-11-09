from __future__ import annotations

import math

import numpy as np

from app.core.pose.base import SIDE_JOINT_MAP, Person


def calculate_angle(
    a: tuple[float, float] | np.ndarray,
    b: tuple[float, float] | np.ndarray,
    c: tuple[float, float] | np.ndarray,
) -> float:
    """
    Calculate the interior angle ABC (in degrees, [0, 180]) with vertex at b
    using atan2.
    """
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    cx, cy = float(c[0]), float(c[1])

    ang_a = math.atan2(ay - by, ax - bx)
    ang_c = math.atan2(cy - by, cx - bx)
    angle_deg = abs(math.degrees(ang_a - ang_c))
    if angle_deg > 180.0:
        angle_deg = 360.0 - angle_deg
    return angle_deg


def distance(
    p1: tuple[float, float] | np.ndarray,
    p2: tuple[float, float] | np.ndarray,
) -> float:
    """Euclidean distance between two 2D points."""
    dx = float(p1[0]) - float(p2[0])
    dy = float(p1[1]) - float(p2[1])
    return math.hypot(dx, dy)


def midpoint(
    p1: tuple[float, float] | np.ndarray,
    p2: tuple[float, float] | np.ndarray,
) -> np.ndarray:
    """Midpoint between two 2D points."""
    return np.array(
        [(float(p1[0]) + float(p2[0])) * 0.5, (float(p1[1]) + float(p2[1])) * 0.5],
        dtype=np.float32,
    )


def torso_length(person: Person, side: str = "right") -> float:
    """
    Compute the reference torso length (shoulder to hip distance) for normalization.
    Falls back to average of both sides or bounding box height if needed.
    """
    sh_idx = SIDE_JOINT_MAP[side]["shoulder"]
    hp_idx = SIDE_JOINT_MAP[side]["hip"]
    length = distance(person.keypoints[sh_idx], person.keypoints[hp_idx])
    if length > 1e-3:
        return length

    other_side = "left" if side == "right" else "right"
    sh_idx2 = SIDE_JOINT_MAP[other_side]["shoulder"]
    hp_idx2 = SIDE_JOINT_MAP[other_side]["hip"]
    length2 = distance(person.keypoints[sh_idx2], person.keypoints[hp_idx2])
    if length2 > 1e-3:
        return length2

    _, y1, _, y2 = person.bbox
    return max(1.0, (y2 - y1) * 0.35)


def normalize_distance(dist_px: float, ref_torso_px: float) -> float:
    """Normalize a pixel distance by the person's torso length."""
    return dist_px / max(1.0, ref_torso_px)


def point_to_line_distance(
    point: tuple[float, float] | np.ndarray,
    line_start: tuple[float, float] | np.ndarray,
    line_end: tuple[float, float] | np.ndarray,
) -> float:
    """Perpendicular distance from `point` to the line through `line_start` and `line_end`."""
    px, py = float(point[0]), float(point[1])
    x1, y1 = float(line_start[0]), float(line_start[1])
    x2, y2 = float(line_end[0]), float(line_end[1])

    denom = math.hypot(x2 - x1, y2 - y1)
    if denom < 1e-6:
        return math.hypot(px - x1, py - y1)
    num = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
    return num / denom


def vertical_angle(
    upper_point: tuple[float, float] | np.ndarray,
    lower_point: tuple[float, float] | np.ndarray,
) -> float:
    """
    Angle (in degrees, [0, 180]) between the vector (lower_point -> upper_point)
    and the upward vertical axis (0, -1) in image coordinates.
    0° means perfectly vertical upright.
    """
    dx = float(upper_point[0]) - float(lower_point[0])
    dy = float(lower_point[1]) - float(
        upper_point[1]
    )  # positive when upper_point is higher (smaller y)
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        return 0.0
    cos_theta = max(-1.0, min(1.0, dy / norm))
    return math.degrees(math.acos(cos_theta))
