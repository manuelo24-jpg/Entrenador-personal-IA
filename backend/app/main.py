from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.exercises import router as exercises_router
from app.api.jobs import router as jobs_router
from app.api.live import router as live_router
from app.api.videos import router as videos_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="EPIA — Entrenador Personal de Inteligencia Artificial",
    description=(
        "API de análisis biomecánico, conteo de repeticiones y corrección postural "
        "mediante visión por computador (YOLO11-pose)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(exercises_router)
app.include_router(jobs_router)
app.include_router(videos_router)
app.include_router(live_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": "EPIA",
        "full_name": "Entrenador Personal de Inteligencia Artificial",
    }
