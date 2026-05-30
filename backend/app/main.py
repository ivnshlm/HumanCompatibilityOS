import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import (
    audit,
    auth,
    calibration,
    compliance,
    dashboard,
    export,
    health,
    questionnaire,
    recalibration,
    users,
)

settings = get_settings()
logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP: create tables on startup. Replaced by Alembic migrations later.
    init_db()
    yield


app = FastAPI(
    title="Human Compatibility OS API",
    version="0.1.0",
    description="Explainability-first operational compatibility & burnout monitoring (MVP).",
    lifespan=lifespan,
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(questionnaire.router)
app.include_router(dashboard.router)
app.include_router(recalibration.router)
app.include_router(users.router)
app.include_router(calibration.router)
app.include_router(audit.router)
app.include_router(compliance.router)
app.include_router(export.router)


@app.get("/")
def root() -> dict:
    return {"service": "human-compatibility-os", "version": app.version, "docs": "/docs"}
