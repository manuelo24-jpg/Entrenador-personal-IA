from __future__ import annotations

import numpy as np
import pytest

from app.core.geometry import (
    calculate_angle,
    distance,
    midpoint,
    normalize_distance,
    point_to_line_distance,
    torso_length,
    vertical_angle,
)
from app.core.pose.base import Person
from app.core.smoothing import KeypointSmoother, OneEuroFilter1D
from app.core.tracking import PersonTracker
from app.core.view import detect_view_and_side


def make_synthetic_person(
    shoulder=(200.0, 200.0),
    elbow=(200.0, 300.0),
    wrist=(200.0, 400.0),
    hip=(200.0, 420.0),
    knee=(200.0, 560.0),
    ankle=(200.0, 700.0),
    conf: float = 0.95,
    track_id: int = 1,
    bbox=(140.0, 150.0, 260.0, 720.0),
) -> Person:
    kpts = np.zeros((17, 2), dtype=np.float32)
    confs = np.full(17, conf, dtype=np.float32)

    # Set both left and right sides (slightly offset for side profile)
    for side_offset, indices in [
        (0.0, (6, 8, 10, 12, 14, 16)),
        (10.0, (5, 7, 9, 11, 13, 15)),
    ]:
        sh_i, el_i, wr_i, hp_i, kn_i, an_i = indices
        kpts[sh_i] = (shoulder[0] + side_offset, shoulder[1])
        kpts[el_i] = (elbow[0] + side_offset, elbow[1])
        kpts[wr_i] = (wrist[0] + side_offset, wrist[1])
        kpts[hp_i] = (hip[0] + side_offset, hip[1])
        kpts[kn_i] = (knee[0] + side_offset, knee[1])
        kpts[an_i] = (ankle[0] + side_offset, ankle[1])

    # Ears
    kpts[3] = (shoulder[0], shoulder[1] - 45.0)
    kpts[4] = (shoulder[0], shoulder[1] - 45.0)
    return Person(keypoints=kpts, confidences=confs, bbox=bbox, track_id=track_id)


def test_calculate_angle_known_values():
    assert pytest.approx(calculate_angle((0, 1), (0, 0), (1, 0)), abs=1e-3) == 90.0
    assert pytest.approx(calculate_angle((-1, 0), (0, 0), (1, 0)), abs=1e-3) == 180.0
    assert pytest.approx(calculate_angle((1, 1), (0, 0), (1, 0)), abs=1e-3) == 45.0


def test_torso_normalization_and_line_distance():
    p = make_synthetic_person(shoulder=(100, 100), hip=(100, 300), ankle=(100, 500))
    t_len = torso_length(p, "right")
    assert pytest.approx(t_len, abs=1e-3) == 200.0
    assert pytest.approx(normalize_distance(50.0, t_len), abs=1e-3) == 0.25

    d = point_to_line_distance((150, 300), (100, 100), (100, 500))
    assert pytest.approx(d, abs=1e-3) == 50.0


def test_vertical_angle():
    # Perfectly upright (shoulder directly above hip)
    assert pytest.approx(vertical_angle((200, 100), (200, 300)), abs=1e-3) == 0.0
    # 45 degree forward lean
    assert pytest.approx(vertical_angle((300, 200), (200, 300)), abs=1e-3) == 45.0
    assert list(midpoint((0, 0), (10, 20))) == [5.0, 10.0]
    assert pytest.approx(distance((0, 0), (3, 4)), abs=1e-4) == 5.0


def test_one_euro_filter_and_keypoint_smoother():
    f = OneEuroFilter1D(min_cutoff=1.0, beta=0.01)
    v0 = f(100.0, 0.0)
    v1 = f(110.0, 0.033)
    assert v0 == 100.0
    assert 100.0 < v1 < 110.0

    smoother = KeypointSmoother(max_missing_frames=3)
    p1 = make_synthetic_person()
    s1 = smoother.smooth(p1, 0.0)
    assert np.allclose(s1.keypoints, p1.keypoints)

    # Simulate short confidence drop
    p_drop = make_synthetic_person(shoulder=(999.0, 999.0), conf=0.1)
    s_drop = smoother.smooth(p_drop, 0.033)
    # Should hold previous valid coordinate
    assert pytest.approx(float(s_drop.keypoints[6, 0]), abs=1e-2) == 200.0


def test_person_tracker_and_view_detection():
    tracker = PersonTracker()
    small_edge = make_synthetic_person(bbox=(10.0, 10.0, 60.0, 100.0), track_id=2)
    main_center = make_synthetic_person(bbox=(400.0, 100.0, 800.0, 650.0), track_id=5)

    chosen = tracker.select([small_edge, main_center], 1280, 720)
    assert chosen is not None
    assert chosen.track_id == 5

    view = detect_view_and_side(chosen, 1280, 720, preferred_view="side")
    assert view.is_visible is True
    assert view.placement_status == "ok"
