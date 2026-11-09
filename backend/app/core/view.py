from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.config import CONFIDENCE_THRESHOLD
from app.core.geometry import distance, torso_length
from app.core.pose.base import SIDE_JOINT_MAP, Person


@dataclass
class ViewAnalysis:
    """Detected camera orientation, body side, visibility, and placement assistant advice."""

    dominant_side: str  # "left" | "right"
    detected_view: str  # "side" | "front"
    mean_confidence: float  # [0..1]
    is_visible: bool  # True if required joints have sufficient confidence
    placement_status: (
        str  # "ok" | "low_visibility" | "move_back" | "move_closer" | "turn_side" | "turn_front"
    )
    placement_message: str  # User-facing Spanish instruction


def detect_view_and_side(
    person: Person,
    frame_width: int,
    frame_height: int,
    required_joints: list[str] | None = None,
    preferred_view: str = "side",
    conf_threshold: float = CONFIDENCE_THRESHOLD,
) -> ViewAnalysis:
    """
    Determine which side of the body has higher confidence, whether the user is seen
    from profile ('side') or frontal ('front'), and provide camera placement guidance.
    """
    joints = required_joints or ["shoulder", "elbow", "wrist", "hip", "knee", "ankle"]

    left_confs = [
        float(person.confidences[SIDE_JOINT_MAP["left"][j]])
        for j in joints
        if j in SIDE_JOINT_MAP["left"]
    ]
    right_confs = [
        float(person.confidences[SIDE_JOINT_MAP["right"][j]])
        for j in joints
        if j in SIDE_JOINT_MAP["right"]
    ]

    mean_left = float(np.mean(left_confs)) if left_confs else 0.0
    mean_right = float(np.mean(right_confs)) if right_confs else 0.0

    dominant_side = "left" if mean_left > mean_right else "right"
    dominant_confs = left_confs if dominant_side == "left" else right_confs
    mean_conf = max(mean_left, mean_right)

    # Check if shoulder-width / torso-length indicates frontal or side view
    l_sh = person.keypoints[SIDE_JOINT_MAP["left"]["shoulder"]]
    r_sh = person.keypoints[SIDE_JOINT_MAP["right"]["shoulder"]]
    shoulder_width = distance(l_sh, r_sh)
    ref_torso = torso_length(person, dominant_side)
    shoulder_ratio = shoulder_width / max(1.0, ref_torso)

    detected_view = "front" if shoulder_ratio >= 0.52 else "side"

    # Check visibility of required keypoints on dominant side
    min_joint_conf = min(dominant_confs) if dominant_confs else 0.0
    is_visible = mean_conf >= conf_threshold and min_joint_conf >= (conf_threshold * 0.75)

    if not is_visible:
        return ViewAnalysis(
            dominant_side=dominant_side,
            detected_view=detected_view,
            mean_confidence=mean_conf,
            is_visible=False,
            placement_status="low_visibility",
            placement_message=(
                "No se te ve completo: aléjate o mejora la iluminación "
                "para encuadrar todo el cuerpo"
            ),
        )

    # Check bounding box margins against frame edges
    x1, y1, x2, y2 = person.bbox
    margin_x = frame_width * 0.02
    margin_y = frame_height * 0.02
    if (
        x1 < margin_x
        or y1 < margin_y
        or x2 > (frame_width - margin_x)
        or y2 > (frame_height - margin_y)
    ):
        return ViewAnalysis(
            dominant_side=dominant_side,
            detected_view=detected_view,
            mean_confidence=mean_conf,
            is_visible=True,
            placement_status="move_back",
            placement_message="Aléjate un poco de la cámara para no cortar pies ni brazos",
        )

    bbox_span = max(x2 - x1, y2 - y1)
    frame_span = max(1.0, float(max(frame_width, frame_height)))
    if (bbox_span / frame_span) < 0.22:
        return ViewAnalysis(
            dominant_side=dominant_side,
            detected_view=detected_view,
            mean_confidence=mean_conf,
            is_visible=True,
            placement_status="move_closer",
            placement_message="Acércate un poco más a la cámara para mayor precisión",
        )

    if preferred_view == "side" and detected_view == "front" and shoulder_ratio > 0.68:
        return ViewAnalysis(
            dominant_side=dominant_side,
            detected_view=detected_view,
            mean_confidence=mean_conf,
            is_visible=True,
            placement_status="turn_side",
            placement_message=(
                "Colócate de perfil respecto a la cámara para medir mejor los ángulos"
            ),
        )

    if preferred_view == "front" and detected_view == "side":
        return ViewAnalysis(
            dominant_side=dominant_side,
            detected_view=detected_view,
            mean_confidence=mean_conf,
            is_visible=True,
            placement_status="turn_front",
            placement_message="Colócate de frente a la cámara para este ejercicio",
        )

    return ViewAnalysis(
        dominant_side=dominant_side,
        detected_view=detected_view,
        mean_confidence=mean_conf,
        is_visible=True,
        placement_status="ok",
        placement_message="Posición correcta. ¡Listo para entrenar!",
    )
