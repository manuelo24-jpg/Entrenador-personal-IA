from __future__ import annotations

import math

import numpy as np

from app.core.exercises import create_analyzer
from app.core.pose.base import Person


def _person_with_elbow_angle(
    elbow_deg: float,
    hip_sag_px: float = 0.0,
    knee_bend_px: float = 0.0,
) -> Person:
    """
    Create a horizontal side-profile pushup person where shoulder=(300, 300),
    hip=(500, 300 + hip_sag_px), ankle=(700, 300), and elbow angle is `elbow_deg`.
    """
    kpts = np.zeros((17, 2), dtype=np.float32)
    confs = np.full(17, 0.95, dtype=np.float32)

    sh = (300.0, 300.0)
    el = (300.0, 400.0)
    # Vector from elbow to shoulder is (0, -100), i.e. angle -90 deg
    # Place wrist at angle (-90 + elbow_deg) from elbow
    rad = math.radians(-90.0 + elbow_deg)
    wr = (el[0] + 100.0 * math.cos(rad), el[1] + 100.0 * math.sin(rad))

    hp = (500.0, 300.0 + hip_sag_px)
    kn = (600.0, 300.0 + knee_bend_px)
    an = (700.0, 300.0)

    for idx_set in [(6, 8, 10, 12, 14, 16), (5, 7, 9, 11, 13, 15)]:
        kpts[idx_set[0]] = sh
        kpts[idx_set[1]] = el
        kpts[idx_set[2]] = wr
        kpts[idx_set[3]] = hp
        kpts[idx_set[4]] = kn
        kpts[idx_set[5]] = an

    kpts[3] = (250.0, 290.0)
    kpts[4] = (250.0, 290.0)
    return Person(
        keypoints=kpts,
        confidences=confs,
        bbox=(200.0, 200.0, 800.0, 550.0),
        track_id=1,
    )


def test_pushup_clean_reps_and_partial_rep():
    analyzer = create_analyzer("pushup", level="medium")
    t = 0.0

    # 1st rep: clean full range of motion (170 -> 80 -> 170) over 1.2s
    angles_seq = [170, 170, 140, 110, 82, 80, 82, 115, 145, 168, 170]
    for ang in angles_seq:
        p = _person_with_elbow_angle(float(ang))
        analyzer.analyze_frame(p, timestamp=t)
        t += 0.12

    assert len(analyzer.reps) == 1
    assert analyzer.reps[0].status == "ok"
    assert analyzer.reps[0].score == 100.0

    # 2nd rep: partial ROM (only goes down to 112 deg, whereas medium requires <= 90 deg)
    partial_seq = [170, 135, 115, 112, 115, 140, 168, 170]
    for ang in partial_seq:
        p = _person_with_elbow_angle(float(ang))
        analyzer.analyze_frame(p, timestamp=t)
        t += 0.12

    assert len(analyzer.reps) == 2
    assert analyzer.reps[1].status == "partial"
    rule_ids = [e["rule_id"] for e in analyzer.reps[1].errors]
    assert "full_rom" in rule_ids


def test_pushup_hip_sag_and_body_line_errors():
    analyzer = create_analyzer("pushup", level="medium")
    t = 0.0

    # Perform a rep with severe hip sag (80px sag on 200px torso = 0.40 ratio > 0.20 limit)
    for ang in [170, 170, 130, 85, 82, 85, 130, 168, 170]:
        p = _person_with_elbow_angle(float(ang), hip_sag_px=80.0)
        analyzer.analyze_frame(p, timestamp=t)
        t += 0.15

    assert len(analyzer.reps) == 1
    rep = analyzer.reps[0]
    assert rep.status == "bad"
    assert rep.score < 80.0
    error_ids = {e["rule_id"] for e in rep.errors}
    assert "body_line" in error_ids
    assert "hip_position" in error_ids


def test_plank_isometric_hold_timer():
    analyzer = create_analyzer("plank", level="medium")
    p = _person_with_elbow_angle(90.0, hip_sag_px=0.0)

    for step in range(11):
        analyzer.analyze_frame(p, timestamp=step * 0.5)

    summary = analyzer.summarize()
    assert summary.hold_seconds >= 4.5
    assert summary.score_avg >= 95.0


def test_all_five_exercises_instantiate_all_levels():
    for ex in ("pushup", "squat", "situp", "plank", "lunge"):
        for lvl in ("easy", "medium", "advanced"):
            inst = create_analyzer(ex, level=lvl)
            assert inst.exercise_name == ex
            assert inst.level == lvl
