from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
CONFIGS_DIR = BACKEND_DIR / "configs" / "exercises"
MODELS_DIR = BACKEND_DIR / "models"
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_ORIG_DIR = DATA_DIR / "videos" / "original"
VIDEOS_PROC_DIR = DATA_DIR / "videos" / "processed"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "epia.db"

DEFAULT_POSE_MODEL = "yolo11n-pose.pt"
CONFIDENCE_THRESHOLD = 0.50


def ensure_data_dirs() -> None:
    """Create all required local storage directories if they do not exist."""
    for folder in (
        DATA_DIR,
        VIDEOS_ORIG_DIR,
        VIDEOS_PROC_DIR,
        THUMBNAILS_DIR,
        REPORTS_DIR,
        MODELS_DIR,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def load_exercise_config(exercise_name: str) -> dict[str, Any]:
    """Load YAML configuration for a given exercise."""
    yaml_path = CONFIGS_DIR / f"{exercise_name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Configuración de ejercicio no encontrada: {yaml_path}")
    with yaml_path.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


def list_exercise_configs() -> list[dict[str, Any]]:
    """Return all available exercise configurations sorted by filename."""
    configs: list[dict[str, Any]] = []
    if not CONFIGS_DIR.exists():
        return configs
    for path in sorted(CONFIGS_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as fh:
            configs.append(yaml.safe_load(fh))
    return configs
