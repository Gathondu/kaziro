"""FastAPI application factory.

Phase 0 wiring only: structlog + metrics + health/metrics routes. Future
phases (T1.x onwards) extend this module — never duplicate the lifespan
or middleware setup elsewhere.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import health as health_routes
from backend.api import metrics as metrics_routes
from backend.config import Settings, get_settings
from backend.logging_config import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    log.info(
        "app.startup",
        app_env=str(settings.APP_ENV),
        log_format=str(settings.LOG_FORMAT),
        log_level=settings.LOG_LEVEL,
    )
    yield
    log.info("app.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the FastAPI application instance."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Kaziro API",
        version="0.1.0",
        lifespan=_lifespan,
        # Hide the OpenAPI docs in production — toggled properly in T3.10.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(o).rstrip("/") for o in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-Id"],
        )

    app.include_router(health_routes.router)
    app.include_router(metrics_routes.router, prefix=settings.PROMETHEUS_METRICS_PATH)

    return app


# ASGI entry-point for ``uvicorn backend.main:app`` and Docker.
app: Final[FastAPI] = create_app()


__all__ = ["app", "create_app"]
