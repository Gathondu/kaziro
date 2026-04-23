"""Global + per-route sliding-window rate limits (Redis)."""

from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.api.schemas.common import error_envelope
from backend.config import get_settings
from backend.logging_config import get_logger
from backend.services import rate_limit as rate_limit_service
from backend.services.auth import _claims_from_payload, _decode_jwt

log = get_logger(__name__)

# (path prefix, max hits per window, window seconds) — longest prefix wins.
_ROUTE_OVERRIDES: tuple[tuple[str, int, int], ...] = (
    ("/auth/", 30, 60),
    ("/api/v1/jobs", 60, 60),
    ("/api/v1/applications", 60, 60),
)


def _user_id_from_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        settings = get_settings()
        payload = _decode_jwt(token, settings)
        claims = _claims_from_payload(payload)
        return str(claims.user_id)
    except Exception:
        return None


def _client_ip(request: Request) -> str:
    client = request.client
    if client is None:
        return "unknown"
    try:
        return str(ipaddress.ip_address(client.host))
    except ValueError:
        return client.host


def _limit_for_path(path: str) -> tuple[int, int]:
    for prefix, mx, win in _ROUTE_OVERRIDES:
        if path.startswith(prefix):
            return mx, win
    return 100, 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if get_settings().is_test:
            return await call_next(request)
        path = request.url.path
        if (
            path.startswith("/health")
            or path.startswith("/metrics")
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi.json")
        ):
            return await call_next(request)

        mx, window = _limit_for_path(path)
        if path.startswith("/auth/"):
            ident = f"ip:{_client_ip(request)}"
        else:
            uid = _user_id_from_bearer(request)
            ident = f"user:{uid}" if uid else f"ip:{_client_ip(request)}"

        key = f"rl:{ident}:{path.split('?')[0]}"
        allowed, retry_after = await rate_limit_service.check_sliding_window(
            key=key, window_seconds=window, max_hits=mx
        )
        if not allowed:
            body = error_envelope(
                "rate_limited", "Too many requests. Please slow down."
            ).model_dump()
            return JSONResponse(
                status_code=429,
                content=body,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


__all__ = ["RateLimitMiddleware"]
