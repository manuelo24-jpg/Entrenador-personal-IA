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


class LungeAnalyzer(ExerciseAnalyzer):
    """Biomechanical analyzer for Lunges (Zancadas)."""

    exercise_name = "lunge"

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

        front_knee_angle = calculate_angle(hp, kn, an)
        trunk_lean = vertical_angle(sh, hp)

        ref_torso = torso_length(person, side)
        knee_ankle_dx = abs(float(kn[0]) - float(an[0]))
        knee_over_toe = normalize_distance(knee_ankle_dx, ref_torso)

        angles = {
            "front_knee_angle": front_knee_angle,
            "trunk_lean": trunk_lean,
        }

        violations: list[RuleViolation] = []

        # Rule 1: trunk_vertical
        if "trunk_vertical" in self.rules_enabled:
            max_lean = float(self.level_cfg.get("trunk_lean_max_angle", 20.0))
            if trunk_lean > max_lean:
                sev = min(1.0, (trunk_lean - max_lean) / max(8.0, max_lean))
                violations.append(
                    RuleViolation(
                        rule_id="trunk_vertical",
                        message=self.msg("trunk_vertical"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["shoulder"], jmap["hip"]],
                    )
                )

        # Rule 2: knee_tracking
        if "knee_tracking" in self.rules_enabled and front_knee_angle < 130.0:
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

        ideal_line = ((float(hp[0]), float(hp[1])), (float(hp[0]), float(sh[1])))
        return front_knee_angle, angles, violations, ideal_line
