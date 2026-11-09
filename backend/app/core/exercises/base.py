from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import load_exercise_config
from app.core.pose.base import Person
from app.core.scoring import (
    RepRecord,
    RuleViolation,
    SessionSummary,
    compute_rep_score,
    summarize_session,
)
from app.core.view import ViewAnalysis, detect_view_and_side


@dataclass
class FrameAnalysis:
    """Per-frame output produced by an ExerciseAnalyzer."""

    timestamp: float
    state: str  # "NO_PERSON" | "POSITIONING" | "ACTIVE"
    phase: str  # "UP" | "DOWN" | "HOLD"
    primary_angle: float
    angles: dict[str, float]
    reps_total: int
    reps_ok: int
    reps_partial: int
    reps_bad: int
    hold_seconds: float
    current_score: float
    active_errors: list[dict[str, Any]] = field(default_factory=list)
    joint_states: dict[int, str] = field(default_factory=dict)  # joint_idx -> "ok"|"warn"|"bad"
    ideal_line: tuple[tuple[float, float], tuple[float, float]] | None = None
    completed_rep: RepRecord | None = None
    placement_status: str = "ok"
    placement_message: str = ""
    dominant_side: str = "right"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 3),
            "state": self.state,
            "phase": self.phase,
            "primary_angle": round(self.primary_angle, 1),
            "angles": {k: round(v, 1) for k, v in self.angles.items()},
            "reps_total": self.reps_total,
            "reps_ok": self.reps_ok,
            "reps_partial": self.reps_partial,
            "reps_bad": self.reps_bad,
            "hold_seconds": round(self.hold_seconds, 1),
            "current_score": round(self.current_score, 1),
            "active_errors": self.active_errors,
            "joint_states": {str(k): v for k, v in self.joint_states.items()},
            "ideal_line": self.ideal_line,
            "completed_rep": self.completed_rep.to_dict() if self.completed_rep else None,
            "placement_status": self.placement_status,
            "placement_message": self.placement_message,
            "dominant_side": self.dominant_side,
        }


class ExerciseAnalyzer(ABC):
    """
    Base class for exercise biomechanics analyzers.
    Loads all thresholds and rules from `backend/configs/exercises/<exercise>.yaml`
    and implements a hysteresis-protected repetition state machine.
    """

    exercise_name: str = ""

    def __init__(self, level: str = "medium") -> None:
        self.config = load_exercise_config(self.exercise_name)
        levels_cfg = self.config.get("levels", {})
        if level not in levels_cfg:
            raise ValueError(f"Nivel '{level}' no válido. Opciones: {list(levels_cfg.keys())}")
        self.level = level
        self.level_cfg: dict[str, Any] = levels_cfg[level]
        self.rules_enabled: set[str] = set(self.level_cfg.get("rules_enabled", []))
        self.penalties_cfg: dict[str, float] = self.config.get("penalties", {})
        self.messages_cfg: dict[str, str] = self.config.get("messages", {})
        self.hysteresis: float = float(self.config.get("hysteresis_degrees", 5.0))
        self.confirm_frames: int = int(self.config.get("confirm_frames", 2))
        self.is_isometric: bool = bool(self.config.get("is_isometric", False))
        self.preferred_view: str = str(self.config.get("preferred_view", "side"))
        self.required_keypoints: list[str] = list(
            self.config.get("required_keypoints", ["shoulder", "hip", "knee", "ankle"])
        )

        # FSM state
        self.phase: str = "HOLD" if self.is_isometric else "UP"
        self._down_confirm_count: int = 0
        self._up_confirm_count: int = 0
        self._in_descent: bool = False
        self._rep_start_t: float = 0.0
        self._down_reached_t: float = 0.0
        self._rep_min_angle: float = 180.0
        self._rep_max_angle: float = 0.0
        self._current_rep_violations: dict[str, RuleViolation] = {}

        # Session records
        self.reps: list[RepRecord] = []
        self.error_timeline: list[dict[str, Any]] = []
        self._last_timeline_rule: dict[str, float] = {}
        self.hold_seconds: float = 0.0
        self._last_timestamp: float | None = None
        self._isometric_scores: list[float] = []

    def reset(self) -> None:
        self.phase = "HOLD" if self.is_isometric else "UP"
        self._down_confirm_count = 0
        self._up_confirm_count = 0
        self._in_descent = False
        self._rep_start_t = 0.0
        self._down_reached_t = 0.0
        self._rep_min_angle = 180.0
        self._rep_max_angle = 0.0
        self._current_rep_violations.clear()
        self.reps.clear()
        self.error_timeline.clear()
        self._last_timeline_rule.clear()
        self.hold_seconds = 0.0
        self._last_timestamp = None
        self._isometric_scores.clear()

    def msg(self, rule_id: str) -> str:
        return self.messages_cfg.get(rule_id, rule_id)

    def _record_violation(self, violation: RuleViolation, timestamp: float) -> None:
        existing = self._current_rep_violations.get(violation.rule_id)
        if existing is None or violation.severity > existing.severity:
            self._current_rep_violations[violation.rule_id] = violation

        # Avoid spamming timeline with identical error within 1.5 seconds
        last_t = self._last_timeline_rule.get(violation.rule_id, -999.0)
        if (timestamp - last_t) >= 1.5:
            self._last_timeline_rule[violation.rule_id] = timestamp
            self.error_timeline.append(
                {
                    "timestamp": round(timestamp, 2),
                    "rule_id": violation.rule_id,
                    "message": violation.message,
                    "severity": round(violation.severity, 2),
                }
            )

    @abstractmethod
    def compute_metrics(
        self, person: Person, view: ViewAnalysis
    ) -> tuple[
        float,
        dict[str, float],
        list[RuleViolation],
        tuple[tuple[float, float], tuple[float, float]] | None,
    ]:
        """
        Compute exercise-specific angles and rule violations for the current frame.
        Returns: (primary_angle, angles_dict, violations_list, ideal_line)
        """

    def analyze_frame(
        self,
        person: Person | None,
        timestamp: float,
        frame_width: int = 1280,
        frame_height: int = 720,
    ) -> FrameAnalysis:
        """Process a single frame and update the repetition FSM and scoring."""
        dt = 0.0 if self._last_timestamp is None else max(0.0, timestamp - self._last_timestamp)
        self._last_timestamp = timestamp

        if person is None:
            return FrameAnalysis(
                timestamp=timestamp,
                state="NO_PERSON",
                phase=self.phase,
                primary_angle=0.0,
                angles={},
                reps_total=len(self.reps),
                reps_ok=sum(1 for r in self.reps if r.status == "ok"),
                reps_partial=sum(1 for r in self.reps if r.status == "partial"),
                reps_bad=sum(1 for r in self.reps if r.status == "bad"),
                hold_seconds=self.hold_seconds,
                current_score=self._latest_score(),
                placement_status="low_visibility",
                placement_message="No se detecta ninguna persona en cámara",
            )

        view = detect_view_and_side(
            person,
            frame_width=frame_width,
            frame_height=frame_height,
            required_joints=self.required_keypoints,
            preferred_view=self.preferred_view,
        )

        if not view.is_visible:
            return FrameAnalysis(
                timestamp=timestamp,
                state="POSITIONING",
                phase=self.phase,
                primary_angle=0.0,
                angles={},
                reps_total=len(self.reps),
                reps_ok=sum(1 for r in self.reps if r.status == "ok"),
                reps_partial=sum(1 for r in self.reps if r.status == "partial"),
                reps_bad=sum(1 for r in self.reps if r.status == "bad"),
                hold_seconds=self.hold_seconds,
                current_score=self._latest_score(),
                placement_status=view.placement_status,
                placement_message=view.placement_message,
                dominant_side=view.dominant_side,
            )

        primary_angle, angles, frame_violations, ideal_line = self.compute_metrics(person, view)

        # Build joint coloring map
        joint_states: dict[int, str] = {}
        for idx in range(17):
            joint_states[idx] = "ok"
        for v in frame_violations:
            state_label = "bad" if v.severity >= 0.45 else "warn"
            for j_idx in v.joint_indices:
                if joint_states.get(j_idx) != "bad":
                    joint_states[j_idx] = state_label

        completed_rep: RepRecord | None = None

        if self.is_isometric:
            # Isometric mode (e.g. Plank): accumulate valid hold time
            for v in frame_violations:
                self._record_violation(v, timestamp)
            frame_score, _ = compute_rep_score(
                {v.rule_id: v for v in frame_violations},
                self.penalties_cfg,
            )
            self._isometric_scores.append(frame_score)
            if frame_score >= 65.0:
                self.hold_seconds += dt
        else:
            completed_rep = self._update_dynamic_fsm(
                primary_angle=primary_angle,
                frame_violations=frame_violations,
                timestamp=timestamp,
            )

        active_errors = [
            {
                "rule_id": v.rule_id,
                "message": v.message,
                "severity": round(v.severity, 2),
            }
            for v in frame_violations
        ]

        return FrameAnalysis(
            timestamp=timestamp,
            state="ACTIVE",
            phase=self.phase,
            primary_angle=primary_angle,
            angles=angles,
            reps_total=len(self.reps),
            reps_ok=sum(1 for r in self.reps if r.status == "ok"),
            reps_partial=sum(1 for r in self.reps if r.status == "partial"),
            reps_bad=sum(1 for r in self.reps if r.status == "bad"),
            hold_seconds=self.hold_seconds,
            current_score=self._latest_score(),
            active_errors=active_errors,
            joint_states=joint_states,
            ideal_line=ideal_line,
            completed_rep=completed_rep,
            placement_status=view.placement_status,
            placement_message=view.placement_message,
            dominant_side=view.dominant_side,
        )

    def _update_dynamic_fsm(
        self,
        primary_angle: float,
        frame_violations: list[RuleViolation],
        timestamp: float,
    ) -> RepRecord | None:
        up_thresh = float(self.level_cfg["up_threshold"])
        down_thresh = float(self.level_cfg["down_threshold"])
        min_phase_s = float(self.level_cfg.get("min_phase_seconds", 0.0))

        # Begin tracking a repetition once angle drops significantly below up_threshold
        start_descent_thresh = up_thresh - max(12.0, self.hysteresis * 2.0)

        if self.phase == "UP":
            if primary_angle < start_descent_thresh:
                if not self._in_descent:
                    self._in_descent = True
                    self._rep_start_t = timestamp
                    self._rep_min_angle = primary_angle
                    self._rep_max_angle = primary_angle
                    self._current_rep_violations.clear()
                else:
                    self._rep_min_angle = min(self._rep_min_angle, primary_angle)
                    self._rep_max_angle = max(self._rep_max_angle, primary_angle)

                for v in frame_violations:
                    self._record_violation(v, timestamp)

            if primary_angle <= down_thresh:
                self._down_confirm_count += 1
                if self._down_confirm_count >= self.confirm_frames:
                    self.phase = "DOWN"
                    self._down_reached_t = timestamp
                    self._up_confirm_count = 0
            else:
                self._down_confirm_count = 0

                # Detect partial rep (started descent and returned to UP before down_thresh)
                mid_thresh = (up_thresh + down_thresh) * 0.5 + 10.0
                if (
                    self._in_descent
                    and self._rep_min_angle < mid_thresh
                    and primary_angle >= up_thresh
                ):
                    self._up_confirm_count += 1
                    if self._up_confirm_count >= self.confirm_frames:
                        if "full_rom" in self.rules_enabled:
                            shortfall = max(1.0, self._rep_min_angle - down_thresh)
                            sev = min(1.0, shortfall / 25.0)
                            self._record_violation(
                                RuleViolation(
                                    rule_id="full_rom",
                                    message=self.msg("full_rom"),
                                    severity=sev,
                                ),
                                timestamp,
                            )
                        return self._finalize_rep(timestamp, primary_angle)

        elif self.phase == "DOWN":
            self._rep_min_angle = min(self._rep_min_angle, primary_angle)
            self._rep_max_angle = max(self._rep_max_angle, primary_angle)
            for v in frame_violations:
                self._record_violation(v, timestamp)

            if primary_angle >= (up_thresh - self.hysteresis):
                self._up_confirm_count += 1
                if self._up_confirm_count >= self.confirm_frames:
                    # Check tempo rule if enabled
                    rep_duration = max(0.0, timestamp - self._rep_start_t)
                    if "tempo" in self.rules_enabled and min_phase_s > 0.0:
                        if rep_duration < min_phase_s:
                            sev = min(1.0, (min_phase_s - rep_duration) / max(0.1, min_phase_s))
                            self._record_violation(
                                RuleViolation(
                                    rule_id="tempo",
                                    message=self.msg("tempo"),
                                    severity=max(0.4, sev),
                                ),
                                timestamp,
                            )
                    return self._finalize_rep(timestamp, primary_angle)
            else:
                self._up_confirm_count = 0

        return None

    def _finalize_rep(self, timestamp: float, current_angle: float) -> RepRecord:
        self._rep_max_angle = max(self._rep_max_angle, current_angle)
        score, status = compute_rep_score(self._current_rep_violations, self.penalties_cfg)
        errors_list = [
            {
                "rule_id": v.rule_id,
                "message": v.message,
                "severity": round(v.severity, 2),
            }
            for v in self._current_rep_violations.values()
        ]
        rep = RepRecord(
            index=len(self.reps) + 1,
            start_t=self._rep_start_t,
            end_t=timestamp,
            min_angle=self._rep_min_angle,
            max_angle=self._rep_max_angle,
            score=score,
            status=status,
            errors=errors_list,
        )
        self.reps.append(rep)

        # Reset FSM for next repetition
        self.phase = "UP"
        self._in_descent = False
        self._down_confirm_count = 0
        self._up_confirm_count = 0
        self._current_rep_violations.clear()
        return rep

    def _latest_score(self) -> float:
        if self.is_isometric:
            if not self._isometric_scores:
                return 100.0
            return float(sum(self._isometric_scores) / len(self._isometric_scores))
        if not self.reps:
            return 100.0
        return float(sum(r.score for r in self.reps) / len(self.reps))

    def summarize(self) -> SessionSummary:
        iso_score = (
            float(sum(self._isometric_scores) / len(self._isometric_scores))
            if self._isometric_scores
            else 100.0
        )
        return summarize_session(
            exercise=self.exercise_name,
            level=self.level,
            reps=self.reps,
            hold_seconds=self.hold_seconds,
            is_isometric=self.is_isometric,
            isometric_score=iso_score,
            error_timeline=self.error_timeline,
        )
