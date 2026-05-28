import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import init_db
from app.routers import auth, health

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

app.include_router(health.router)
app.include_router(auth.router)


@app.get("/")
def root() -> dict:
    return {"service": "human-compatibility-os", "version": app.version, "docs": "/docs"}
