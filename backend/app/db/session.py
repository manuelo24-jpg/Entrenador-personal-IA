from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DB_PATH, ensure_data_dirs
from app.db.models import Base

ensure_data_dirs()

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create database tables and run lightweight column migrations if needed."""
    ensure_data_dirs()
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "videos" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("videos")}
        if "user_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE videos ADD COLUMN user_id VARCHAR(36)"))


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
