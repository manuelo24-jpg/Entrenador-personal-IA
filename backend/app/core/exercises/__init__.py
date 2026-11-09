from __future__ import annotations

from app.core.exercises.base import ExerciseAnalyzer, FrameAnalysis
from app.core.exercises.lunge import LungeAnalyzer
from app.core.exercises.plank import PlankAnalyzer
from app.core.exercises.pushup import PushupAnalyzer
from app.core.exercises.situp import SitupAnalyzer
from app.core.exercises.squat import SquatAnalyzer

ANALYZER_REGISTRY: dict[str, type[ExerciseAnalyzer]] = {
    "pushup": PushupAnalyzer,
    "squat": SquatAnalyzer,
    "situp": SitupAnalyzer,
    "plank": PlankAnalyzer,
    "lunge": LungeAnalyzer,
}


def create_analyzer(exercise: str, level: str = "medium") -> ExerciseAnalyzer:
    """Instantiate the analyzer for the requested exercise and difficulty level."""
    key = exercise.lower().strip()
    if key not in ANALYZER_REGISTRY:
        raise ValueError(
            f"Ejercicio '{exercise}' no soportado. Disponibles: {list(ANALYZER_REGISTRY.keys())}"
        )
    return ANALYZER_REGISTRY[key](level=level)


__all__ = [
    "ANALYZER_REGISTRY",
    "ExerciseAnalyzer",
    "FrameAnalysis",
    "LungeAnalyzer",
    "PlankAnalyzer",
    "PushupAnalyzer",
    "SitupAnalyzer",
    "SquatAnalyzer",
    "create_analyzer",
]
