from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleViolation:
    """Represents a single biomechanical rule violation with normalized severity [0..1]."""

    rule_id: str
    message: str
    severity: float  # 0.0 (minor) to 1.0 (severe)
    joint_indices: list[int] = field(default_factory=list)


@dataclass
class RepRecord:
    """Complete evaluation of a single repetition (or isometric interval)."""

    index: int
    start_t: float
    end_t: float
    min_angle: float
    max_angle: float
    score: float
    status: str  # "ok" | "partial" | "bad"
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_t - self.start_t)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "start_t": round(self.start_t, 2),
            "end_t": round(self.end_t, 2),
            "duration_s": round(self.duration_s, 2),
            "min_angle": round(self.min_angle, 1),
            "max_angle": round(self.max_angle, 1),
            "score": round(self.score, 1),
            "status": self.status,
            "errors": self.errors,
        }


@dataclass
class SessionSummary:
    """Aggregated metrics and insights for a completed training session."""

    exercise: str
    level: str
    reps_total: int
    reps_ok: int
    reps_partial: int
    reps_bad: int
    hold_seconds: float
    score_avg: float
    top_errors: list[dict[str, Any]]
    fatigue_detected: bool
    advice: str
    reps: list[RepRecord]
    error_timeline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "exercise": self.exercise,
            "level": self.level,
            "reps_total": self.reps_total,
            "reps_ok": self.reps_ok,
            "reps_partial": self.reps_partial,
            "reps_bad": self.reps_bad,
            "hold_seconds": round(self.hold_seconds, 1),
            "score_avg": round(self.score_avg, 1),
            "top_errors": self.top_errors,
            "fatigue_detected": self.fatigue_detected,
            "advice": self.advice,
            "reps": [r.to_dict() for r in self.reps],
            "error_timeline": self.error_timeline,
        }


def compute_rep_score(
    violations_by_rule: dict[str, RuleViolation],
    penalties_cfg: dict[str, float],
) -> tuple[float, str]:
    """
    Calculate repetition score in [0, 100] from accumulated peak violations:
        score = 100 - sum(penalty(rule) * severity)
    Returns (score, status) where status is 'ok', 'partial', or 'bad'.
    """
    total_Deduction = 0.0
    has_rom_error = "full_rom" in violations_by_rule

    for rule_id, violation in violations_by_rule.items():
        base_penalty = float(penalties_cfg.get(rule_id, 20.0))
        sev = max(0.25, min(1.0, violation.severity))
        total_Deduction += base_penalty * sev

    score = max(0.0, min(100.0, 100.0 - total_Deduction))

    if has_rom_error:
        status = "partial"
    elif score >= 75.0 and not violations_by_rule or score >= 80.0:
        status = "ok"
    else:
        status = "bad"

    return score, status


def summarize_session(
    exercise: str,
    level: str,
    reps: list[RepRecord],
    hold_seconds: float = 0.0,
    is_isometric: bool = False,
    isometric_score: float = 100.0,
    error_timeline: list[dict[str, Any]] | None = None,
) -> SessionSummary:
    """Build a complete SessionSummary including fatigue trend and top error breakdown."""
    timeline = error_timeline or []
    reps_total = len(reps)
    reps_ok = sum(1 for r in reps if r.status == "ok")
    reps_partial = sum(1 for r in reps if r.status == "partial")
    reps_bad = sum(1 for r in reps if r.status == "bad")

    if is_isometric:
        score_avg = isometric_score
    elif reps:
        score_avg = sum(r.score for r in reps) / len(reps)
    else:
        score_avg = 0.0

    error_counter: Counter[str] = Counter()
    error_messages: dict[str, str] = {}
    for r in reps:
        for err in r.errors:
            rid = err["rule_id"]
            error_counter[rid] += 1
            error_messages[rid] = err["message"]

    for ev in timeline:
        rid = ev.get("rule_id")
        if rid and not reps:
            error_counter[rid] += 1
            error_messages[rid] = ev.get("message", rid)

    top_errors = [
        {
            "rule_id": rid,
            "message": error_messages.get(rid, rid),
            "count": count,
        }
        for rid, count in error_counter.most_common(5)
    ]

    # Fatigue detection: compare last third of reps against first third
    fatigue_detected = False
    if len(reps) >= 4:
        split = max(2, len(reps) // 2)
        first_half_avg = sum(r.score for r in reps[:split]) / split
        second_half_avg = sum(r.score for r in reps[-split:]) / split
        if (first_half_avg - second_half_avg) >= 12.0:
            fatigue_detected = True

    if is_isometric:
        if hold_seconds <= 0.1:
            advice = "Mantén la posición de plancha dentro del encuadre para registrar el tiempo."
        elif top_errors:
            advice = f"Tiempo efectivo: {hold_seconds:.1f}s. Prioriza: {top_errors[0]['message']}."
        else:
            advice = f"¡Excelente control postural en plancha durante {hold_seconds:.1f}s!"
    elif not reps:
        advice = "No se completaron repeticiones. Asegúrate de encuadrar todo el cuerpo de perfil."
    elif top_errors:
        main_msg = top_errors[0]["message"]
        if fatigue_detected:
            advice = f"Se detecta fatiga al final de la serie. Foco principal: {main_msg}."
        else:
            advice = f"Consejo principal para tu próxima serie: {main_msg}."
    else:
        advice = "¡Ejecución impecable! Todas las repeticiones dentro de los rangos óptimos."

    return SessionSummary(
        exercise=exercise,
        level=level,
        reps_total=reps_total,
        reps_ok=reps_ok,
        reps_partial=reps_partial,
        reps_bad=reps_bad,
        hold_seconds=hold_seconds,
        score_avg=score_avg,
        top_errors=top_errors,
        fatigue_detected=fatigue_detected,
        advice=advice,
        reps=reps,
        error_timeline=timeline,
    )
