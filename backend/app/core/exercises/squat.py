from __future__ import annotations

from app.core.exercises.base import ExerciseAnalyzer
from app.core.geometry import (
    calculate_angle,
    normalize_distance,
    torso_length,
    vertical_angle,
)
from app.core.pose.base import SIDE_JOINT_MAP, Person
from app.core.scoring import RuleViolation
from app.core.view import ViewAnalysis


class SquatAnalyzer(ExerciseAnalyzer):
    """Biomechanical analyzer for Squats (Sentadillas)."""

    exercise_name = "squat"

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
        hp = person.keypoints[jmap["hip"]]
        kn = person.keypoints[jmap["knee"]]
        an = person.keypoints[jmap["ankle"]]

        knee_angle = calculate_angle(hp, kn, an)
        hip_angle = calculate_angle(sh, hp, kn)
        trunk_lean = vertical_angle(sh, hp)

        ref_torso = torso_length(person, side)
        # Horizontal distance between knee and ankle normalized by torso length
        knee_ankle_dx = abs(float(kn[0]) - float(an[0]))
        knee_over_toe = normalize_distance(knee_ankle_dx, ref_torso)

        angles = {
            "knee_angle": knee_angle,
            "hip_angle": hip_angle,
            "trunk_lean": trunk_lean,
        }

        violations: list[RuleViolation] = []

        # Rule 1: trunk_lean (excessive forward torso inclination)
        if "trunk_lean" in self.rules_enabled:
            max_lean = float(self.level_cfg.get("trunk_lean_max_angle", 40.0))
            if trunk_lean > max_lean:
                sev = min(1.0, (trunk_lean - max_lean) / max(10.0, max_lean * 0.5))
                violations.append(
                    RuleViolation(
                        rule_id="trunk_lean",
                        message=self.msg("trunk_lean"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["shoulder"], jmap["hip"]],
                    )
                )

        # Rule 2: knee_tracking (normalized horizontal projection of knee relative to ankle)
        if "knee_tracking" in self.rules_enabled and knee_angle < 135.0:
            max_ratio = float(self.level_cfg.get("knee_over_toe_ratio", 0.25))
            if knee_over_toe > max_ratio:
                sev = min(1.0, (knee_over_toe - max_ratio) / max(0.08, max_ratio))
                violations.append(
                    RuleViolation(
                        rule_id="knee_tracking",
                        message=self.msg("knee_tracking"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["knee"], jmap["ankle"]],
                    )
                )

        # Rule 3: symmetry (compare left vs right knee angles if visible)
        if "symmetry" in self.rules_enabled:
            other_side = "left" if side == "right" else "right"
            oj = SIDE_JOINT_MAP[other_side]
            if (
                person.confidences[oj["hip"]] >= 0.5
                and person.confidences[oj["knee"]] >= 0.5
                and person.confidences[oj["ankle"]] >= 0.5
            ):
                other_knee = calculate_angle(
                    person.keypoints[oj["hip"]],
                    person.keypoints[oj["knee"]],
                    person.keypoints[oj["ankle"]],
                )
                sym_tol = float(self.level_cfg.get("symmetry_tolerance", 10.0))
                diff = abs(knee_angle - other_knee)
                if diff > sym_tol:
                    sev = min(1.0, (diff - sym_tol) / max(5.0, sym_tol))
                    violations.append(
                        RuleViolation(
                            rule_id="symmetry",
                            message=self.msg("symmetry"),
                            severity=max(0.3, sev),
                            joint_indices=[jmap["knee"], oj["knee"]],
                        )
                    )

        # Vertical reference line from ankle upward
        ideal_line = (
            (float(an[0]), float(an[1])),
            (float(an[0]), float(sh[1])),
        )
        return knee_angle, angles, violations, ideal_line
