from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    videos = relationship("VideoModel", back_populates="user")


class VideoModel(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    exercise = Column(String(64), nullable=False, index=True)
    level = Column(String(32), nullable=False, index=True)
    source = Column(String(32), nullable=False, default="upload")  # "upload" | "live"
    original_path = Column(String(512), nullable=False)
    processed_path = Column(String(512), nullable=True)
    thumbnail_path = Column(String(512), nullable=True)
    duration_s = Column(Float, nullable=False, default=0.0)
    fps = Column(Float, nullable=False, default=30.0)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    favorite = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=False, default="")
    status = Column(
        String(32), nullable=False, default="queued"
    )  # queued | processing | done | error
    tags_csv = Column(String(512), nullable=False, default="")

    user = relationship("UserModel", back_populates="videos")
    sessions = relationship(
        "SessionModel",
        back_populates="video",
        cascade="all, delete-orphan",
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, index=True)
    video_id = Column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reps_total = Column(Integer, nullable=False, default=0)
    reps_ok = Column(Integer, nullable=False, default=0)
    reps_partial = Column(Integer, nullable=False, default=0)
    reps_bad = Column(Integer, nullable=False, default=0)
    hold_seconds = Column(Float, nullable=False, default=0.0)
    score_avg = Column(Float, nullable=False, default=0.0)
    report_json = Column(Text, nullable=False, default="{}")

    video = relationship("VideoModel", back_populates="sessions")
    reps = relationship(
        "RepModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class RepModel(Base):
    __tablename__ = "reps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    index = Column(Integer, nullable=False)
    start_t = Column(Float, nullable=False, default=0.0)
    end_t = Column(Float, nullable=False, default=0.0)
    min_angle = Column(Float, nullable=False, default=0.0)
    max_angle = Column(Float, nullable=False, default=0.0)
    score = Column(Float, nullable=False, default=100.0)
    status = Column(String(32), nullable=False, default="ok")
    errors_json = Column(Text, nullable=False, default="[]")

    session = relationship("SessionModel", back_populates="reps")


class SettingModel(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
