from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.config import list_exercise_configs

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
def get_exercises() -> list[dict[str, Any]]:
    """Return the full catalog of supported exercises, levels, and recommended camera views."""
    raw_configs = list_exercise_configs()
    catalog: list[dict[str, Any]] = []

    for cfg in raw_configs:
        levels_out: dict[str, Any] = {}
        for lvl_key, lvl_data in cfg.get("levels", {}).items():
            levels_out[lvl_key] = {
                "key": lvl_key,
                "display_name": lvl_data.get("display_name", lvl_key.capitalize()),
                "rules_enabled": lvl_data.get("rules_enabled", []),
                "up_threshold": lvl_data.get("up_threshold"),
                "down_threshold": lvl_data.get("down_threshold"),
                "target_hold_seconds": lvl_data.get("target_hold_seconds"),
            }
        catalog.append(
            {
                "exercise": cfg.get("exercise"),
                "display_name": cfg.get("display_name"),
                "description": cfg.get("description", ""),
                "icon": cfg.get("icon", "🏋️"),
                "preferred_view": cfg.get("preferred_view", "side"),
                "is_isometric": bool(cfg.get("is_isometric", False)),
                "required_keypoints": cfg.get("required_keypoints", []),
                "levels": levels_out,
                "messages": cfg.get("messages", {}),
            }
        )
    return catalog
