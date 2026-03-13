"""Manga Translator — FastAPI backend entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.model_manager import model_manager
from app.api import health, projects, pipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Loading models into VRAM...")
    try:
        model_manager.load()
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        logger.warning("Backend will start but pipeline will not work until models load.")
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down pipeline worker...")
    from app.core.pipeline_worker import pipeline_worker
    pipeline_worker.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Manga Translator API",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(projects.router, prefix="/projects", tags=["projects"])
    app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])

    return app


app = create_app()