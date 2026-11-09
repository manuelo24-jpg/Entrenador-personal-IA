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


class PushupAnalyzer(ExerciseAnalyzer):
    """Biomechanical analyzer for Push-ups (Flexiones)."""

    exercise_name = "pushup"

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
        wr = person.keypoints[jmap["wrist"]]
        hp = person.keypoints[jmap["hip"]]
        kn = person.keypoints[jmap["knee"]]
        an = person.keypoints[jmap["ankle"]]

        elbow_angle = calculate_angle(sh, el, wr)
        body_line_angle = calculate_angle(sh, hp, an)
        knee_angle = calculate_angle(hp, kn, an)

        ref_torso = torso_length(person, side)
        hip_dist_px = point_to_line_distance(hp, sh, an)
        hip_sag_ratio = normalize_distance(hip_dist_px, ref_torso)

        angles = {
            "elbow_angle": elbow_angle,
            "body_line_angle": body_line_angle,
            "knee_angle": knee_angle,
        }

        violations: list[RuleViolation] = []

        # Rule 1: body_line (hombro-cadera-tobillo ~ 180°)
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

        # Rule 2: hip_position (normalized perpendicular distance of hip to shoulder-ankle line)
        if "hip_position" in self.rules_enabled:
            max_ratio = float(self.level_cfg.get("hip_sag_ratio", 0.20))
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
            min_knee = float(self.level_cfg.get("knee_min_angle", 155.0))
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

        # Rule 4: symmetry (when both arms are visible with sufficient confidence)
        if "symmetry" in self.rules_enabled:
            other_side = "left" if side == "right" else "right"
            oj = SIDE_JOINT_MAP[other_side]
            if (
                person.confidences[oj["shoulder"]] >= 0.5
                and person.confidences[oj["elbow"]] >= 0.5
                and person.confidences[oj["wrist"]] >= 0.5
            ):
                other_elbow = calculate_angle(
                    person.keypoints[oj["shoulder"]],
                    person.keypoints[oj["elbow"]],
                    person.keypoints[oj["wrist"]],
                )
                sym_tol = float(self.level_cfg.get("symmetry_tolerance", 12.0))
                diff = abs(elbow_angle - other_elbow)
                if diff > sym_tol:
                    sev = min(1.0, (diff - sym_tol) / max(5.0, sym_tol))
                    violations.append(
                        RuleViolation(
                            rule_id="symmetry",
                            message=self.msg("symmetry"),
                            severity=max(0.3, sev),
                            joint_indices=[jmap["elbow"], oj["elbow"]],
                        )
                    )

        ideal_line = ((float(sh[0]), float(sh[1])), (float(an[0]), float(an[1])))
        return elbow_angle, angles, violations, ideal_line
