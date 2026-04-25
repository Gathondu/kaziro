"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langsmith.middleware import TracingMiddleware

from backend.api import health as health_routes
from backend.api import metrics as metrics_routes
from backend.api.exceptions import register_exception_handlers
from backend.api.middleware import RateLimitMiddleware, RequestIdMiddleware
from backend.api.router import api_v1_router, auth_router
from backend.config import AppEnv, Settings, get_settings
from backend.logging_config import configure_logging, get_logger
from backend.services.langsmith_tracing import apply_langsmith_tracing_from_settings

log = get_logger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    apply_langsmith_tracing_from_settings(settings)
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
        debug=settings.DEBUG or settings.APP_ENV is AppEnv.DEVELOPMENT,
        # Hide the OpenAPI docs in production
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o).rstrip("/") for o in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "Retry-After"],
    )

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(cast(Any, TracingMiddleware))

    register_exception_handlers(app)

    app.include_router(health_routes.router)
    app.include_router(metrics_routes.router, prefix=settings.PROMETHEUS_METRICS_PATH)
    app.include_router(auth_router)
    app.include_router(api_v1_router)

    return app


# ASGI entry-point for ``uvicorn backend.main:app`` and Docker.
app: Final[FastAPI] = create_app()


__all__ = ["app", "create_app"]
