from __future__ import annotations

import uuid

from app.api.auth import LoginSchema, RegisterSchema, login_user, register_user
from app.api.exercises import get_exercises
from app.api.videos import get_progress_stats, list_videos
from app.core.security import decode_access_token
from app.db.session import SessionLocal, init_db
from app.main import health_check


def test_health_and_exercises_catalog():
    res_health = health_check()
    assert res_health["app"] == "EPIA"
    assert res_health["status"] == "ok"

    catalog = get_exercises()
    assert len(catalog) == 5
    names = {item["exercise"] for item in catalog}
    assert names == {"pushup", "squat", "situp", "plank", "lunge"}


def test_videos_list_and_stats():
    init_db()
    db = SessionLocal()
    try:
        videos = list_videos(db=db, current_user=None)
        assert isinstance(videos, list)

        stats = get_progress_stats(db=db, current_user=None)
        assert "total_sessions" in stats
        assert "avg_score" in stats
    finally:
        db.close()


def test_auth_register_and_login():
    init_db()
    db = SessionLocal()
    try:
        unique_email = f"atleta_{uuid.uuid4().hex[:8]}@epia.local"
        reg_res = register_user(
            RegisterSchema(name="Atleta EPIA", email=unique_email, password="password123"),
            db=db,
        )
        assert "token" in reg_res
        assert reg_res["user"]["email"] == unique_email

        decoded = decode_access_token(reg_res["token"])
        assert decoded is not None
        assert decoded["email"] == unique_email

        login_res = login_user(
            LoginSchema(email=unique_email, password="password123"),
            db=db,
        )
        assert login_res["user"]["name"] == "Atleta EPIA"
    finally:
        db.close()
