from __future__ import annotations

from app.core.exercises.base import ExerciseAnalyzer
from app.core.geometry import (
    calculate_angle,
    distance,
    normalize_distance,
    torso_length,
)
from app.core.pose.base import SIDE_JOINT_MAP, Person
from app.core.scoring import RuleViolation
from app.core.view import ViewAnalysis


class SitupAnalyzer(ExerciseAnalyzer):
    """Biomechanical analyzer for Sit-ups / Crunches (Abdominales)."""

    exercise_name = "situp"

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
        ear = person.keypoints[jmap["ear"]]

        hip_angle = calculate_angle(sh, hp, kn)
        knee_angle = calculate_angle(hp, kn, an)

        ref_torso = torso_length(person, side)
        neck_dist = normalize_distance(distance(ear, sh), ref_torso)

        angles = {
            "hip_angle": hip_angle,
            "knee_angle": knee_angle,
        }

        violations: list[RuleViolation] = []

        # Rule 1: knee_flexion (knees should stay bent near ~90°)
        if "knee_flexion" in self.rules_enabled:
            target = float(self.level_cfg.get("knee_target_angle", 90.0))
            tol = float(self.level_cfg.get("knee_angle_tolerance", 25.0))
            dev = abs(knee_angle - target)
            if dev > tol:
                sev = min(1.0, (dev - tol) / max(10.0, tol))
                violations.append(
                    RuleViolation(
                        rule_id="knee_flexion",
                        message=self.msg("knee_flexion"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["knee"], jmap["ankle"]],
                    )
                )

        # Rule 2: neck_alignment (avoid pulling the head/neck excessively close to shoulders)
        if "neck_alignment" in self.rules_enabled and person.confidences[jmap["ear"]] >= 0.45:
            min_ratio = float(self.level_cfg.get("neck_pull_min_ratio", 0.22))
            if neck_dist < min_ratio:
                sev = min(1.0, (min_ratio - neck_dist) / max(0.05, min_ratio))
                violations.append(
                    RuleViolation(
                        rule_id="neck_alignment",
                        message=self.msg("neck_alignment"),
                        severity=max(0.3, sev),
                        joint_indices=[jmap["ear"], jmap["shoulder"]],
                    )
                )

        ideal_line = ((float(hp[0]), float(hp[1])), (float(kn[0]), float(kn[1])))
        return hip_angle, angles, violations, ideal_line
