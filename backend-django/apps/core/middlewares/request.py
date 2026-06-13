from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

from config.logging import get_logger

log = get_logger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        started = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.path,
        )
        try:
            response = self.get_response(request)
            if hasattr(request, "auth") and request.auth.is_authenticated:  # type: ignore
                structlog.contextvars.bind_contextvars(user_id=str(request.auth.id))  # type: ignore

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response["X-Request-Id"] = request_id
            log.info(
                "http.request.complete",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log.exception("http.request.exception", duration_ms=duration_ms)
            raise
        finally:
            structlog.contextvars.clear_contextvars()


__all__ = ["RequestLoggingMiddleware"]
