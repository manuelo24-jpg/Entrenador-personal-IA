from __future__ import annotations

from app.core.exercises.base import ExerciseAnalyzer
from app.core.geometry import (
    calculate_angle,
    normalize_distance,
    point_to_line_distance,
    torso_length,
)
from app.core.pose.base import SIDE_JOINT_MAP, Person
from app.core.scoring import RuleViolation
from app.core.view import ViewAnalysis


class PlankAnalyzer(ExerciseAnalyzer):
    """Biomechanical analyzer for isometric Plank (Plancha)."""

    exercise_name = "plank"

    def compute_metrics(
        self, person: Person, view: ViewAnalysis
    ) -> tuple[
        float,
        dict[str, float],
        list[RuleViolation],
        tuple[tuple[float, float], tuple[float, float]] | None,
    ]:
        side = view.dominant_side
        jmap = SIDE_JOINT_MAP[side]

        sh = person.keypoints[jmap["shoulder"]]
        el = person.keypoints[jmap["elbow"]]
        hp = person.keypoints[jmap["hip"]]
        kn = person.keypoints[jmap["knee"]]
        an = person.keypoints[jmap["ankle"]]

        body_line_angle = calculate_angle(sh, hp, an)
        knee_angle = calculate_angle(hp, kn, an)

        ref_torso = torso_length(person, side)
        hip_dist_px = point_to_line_distance(hp, sh, an)
        hip_sag_ratio = normalize_distance(hip_dist_px, ref_torso)
        elbow_shoulder_dx = abs(float(el[0]) - float(sh[0]))
        elbow_offset_ratio = normalize_distance(elbow_shoulder_dx, ref_torso)

        angles = {
            "body_line_angle": body_line_angle,
            "knee_angle": knee_angle,
        }

        violations: list[RuleViolation] = []

        # Rule 1: body_line
        if "body_line" in self.rules_enabled:
            tol = float(self.level_cfg.get("body_line_tolerance", 15.0))
            dev = abs(180.0 - body_line_angle)
            if dev > tol:
                sev = min(1.0, (dev - tol) / max(5.0, tol))
                violations.append(
                    RuleViolation(
                        rule_id="body_line",
                        message=self.msg("body_line"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["shoulder"], jmap["hip"], jmap["ankle"]],
                    )
                )

        # Rule 2: hip_position
        if "hip_position" in self.rules_enabled:
            max_ratio = float(self.level_cfg.get("hip_sag_ratio", 0.18))
            if hip_sag_ratio > max_ratio:
                sev = min(1.0, (hip_sag_ratio - max_ratio) / max(0.05, max_ratio))
                violations.append(
                    RuleViolation(
                        rule_id="hip_position",
                        message=self.msg("hip_position"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["hip"]],
                    )
                )

        # Rule 3: knees_straight
        if "knees_straight" in self.rules_enabled:
            min_knee = float(self.level_cfg.get("knee_min_angle", 158.0))
            if knee_angle < min_knee:
                sev = min(1.0, (min_knee - knee_angle) / 25.0)
                violations.append(
                    RuleViolation(
                        rule_id="knees_straight",
                        message=self.msg("knees_straight"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["knee"], jmap["ankle"]],
                    )
                )

        # Rule 4: elbow_alignment (elbows directly under shoulders)
        if "elbow_alignment" in self.rules_enabled:
            max_el_ratio = float(self.level_cfg.get("elbow_under_shoulder_ratio", 0.18))
            if elbow_offset_ratio > max_el_ratio:
                sev = min(1.0, (elbow_offset_ratio - max_el_ratio) / max(0.06, max_el_ratio))
                violations.append(
                    RuleViolation(
                        rule_id="elbow_alignment",
                        message=self.msg("elbow_alignment"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["shoulder"], jmap["elbow"]],
                    )
                )

        ideal_line = ((float(sh[0]), float(sh[1])), (float(an[0]), float(an[1])))
        return body_line_angle, angles, violations, ideal_line
