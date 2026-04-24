"""Liveness, readiness, and detailed health endpoints.

Three endpoints, three audiences:

* ``GET /health`` — Kubernetes liveness probe; cheap, never touches a
  dependency.
* ``GET /health/ready`` — readiness probe; verifies that we can talk to
  Postgres and Redis. A 503 here pulls the pod out of rotation.
* ``GET /health/detailed`` — per-component status JSON for the on-call
  dashboard. Adds Supabase, OpenRouter, and Firecrawl status as best-effort
  reachability checks.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final, Literal

import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import Settings, get_settings
from backend.logging_config import get_logger

router: Final[APIRouter] = APIRouter(tags=["health"])
log = get_logger(__name__)


HealthStatus = Literal["ok", "degraded", "down", "skipped"]


@dataclass(slots=True)
class ComponentStatus:
    name: str
    status: HealthStatus
    latency_ms: int | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
        }


@router.get("/health", summary="Liveness probe", response_model=None)
async def health() -> dict[str, str]:
    """Process-level liveness — return as fast as possible."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe", response_model=None)
async def ready() -> JSONResponse:
    """Readiness — fail closed if Postgres or Redis are unreachable."""
    settings = get_settings()
    pg, rd = await asyncio.gather(
        _check_postgres(settings),
        _check_redis(settings),
    )
    components = [pg, rd]
    overall_ok = all(c.status == "ok" for c in components)
    payload = {
        "status": "ok" if overall_ok else "degraded",
        "components": [c.to_dict() for c in components],
    }
    code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(payload, status_code=code)


@router.get("/health/detailed", summary="Per-component health JSON", response_model=None)
async def detailed() -> JSONResponse:
    """Best-effort reachability for every external dependency."""
    settings = get_settings()
    components = await asyncio.gather(
        _check_postgres(settings),
        _check_redis(settings),
        _check_supabase(settings),
        _check_openrouter(settings),
        _check_firecrawl(settings),
    )
    overall_ok = all(c.status in {"ok", "skipped"} for c in components)
    payload = {
        "status": "ok" if overall_ok else "degraded",
        "app_env": str(settings.APP_ENV),
        "components": [c.to_dict() for c in components],
    }
    return JSONResponse(payload, status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Component checks (private)
# ---------------------------------------------------------------------------


async def _timed(name: str, probe: Callable[[], Awaitable[ComponentStatus]]) -> ComponentStatus:
    start = time.monotonic()
    try:
        result = await probe()
    except Exception as exc:
        log.warning("health.component_failed", component=name, error=str(exc))
        return ComponentStatus(
            name=name,
            status="down",
            latency_ms=int((time.monotonic() - start) * 1000),
            detail=type(exc).__name__,
        )
    if result.latency_ms is None:
        result.latency_ms = int((time.monotonic() - start) * 1000)
    return result


async def _check_postgres(settings: Settings) -> ComponentStatus:
    async def probe() -> ComponentStatus:
        engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        finally:
            await engine.dispose()
        return ComponentStatus(name="postgres", status="ok")

    return await _timed("postgres", probe)


async def _check_redis(settings: Settings) -> ComponentStatus:
    async def probe() -> ComponentStatus:
        # Imported lazily so import-order doesn't fail when redis is absent in
        # the (rare) lightweight test paths that don't need the client.
        from redis.asyncio import Redis

        client = Redis.from_url(str(settings.REDIS_URL), socket_connect_timeout=2)
        try:
            await client.ping()
        finally:
            await client.aclose()
        return ComponentStatus(name="redis", status="ok")

    return await _timed("redis", probe)


async def _check_supabase(settings: Settings) -> ComponentStatus:
    async def probe() -> ComponentStatus:
        url = f"{str(settings.SUPABASE_URL).rstrip('/')}/auth/v1/health"
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
        return ComponentStatus(
            name="supabase",
            status="ok" if resp.status_code < 500 else "degraded",
            detail=f"HTTP {resp.status_code}",
        )

    return await _timed("supabase", probe)


async def _check_openrouter(_settings: Settings) -> ComponentStatus:
    # Avoid a paid chat/embed probe; a lightweight HTTP check suffices for DNS / routing.
    async def probe() -> ComponentStatus:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models")
        return ComponentStatus(
            name="openrouter",
            status="ok" if resp.status_code < 500 else "degraded",
            detail=f"HTTP {resp.status_code}",
        )

    return await _timed("openrouter", probe)


async def _check_firecrawl(settings: Settings) -> ComponentStatus:
    async def probe() -> ComponentStatus:
        base = (
            str(settings.FIRECRAWL_BASE_URL).rstrip("/")
            if settings.FIRECRAWL_BASE_URL
            else "https://api.firecrawl.dev"
        )
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(base)
        return ComponentStatus(
            name="firecrawl",
            status="ok" if resp.status_code < 500 else "degraded",
            detail=f"HTTP {resp.status_code}",
        )

    return await _timed("firecrawl", probe)


__all__ = ["router"]
