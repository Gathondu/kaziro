"""Centralised exception → JSON-envelope mapping.

Routes raise :class:`ApiError` (or subclasses) — never bare
:class:`HTTPException` — and the handler installed by
:func:`register_exception_handlers` formats them into the standard
envelope from ``docs/architecture/04-api-design.md`` §2.2.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.schemas.common import error_envelope
from backend.logging_config import get_logger

log = get_logger(__name__)


class ApiError(HTTPException):
    """Base class for application-defined HTTP errors.

    Carries a stable ``code`` slug used by the frontend for branching
    UX and analytics. Subclasses fix ``status_code`` and ``code``.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(status_code=self.status_code, detail=message, headers=headers)


class NotFoundError(ApiError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(ApiError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ForbiddenError(ApiError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class UnauthorizedError(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class UpstreamError(ApiError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


def _http_status_to_code(status_code: int) -> str:
    """Best-effort fallback ``code`` for stock :class:`HTTPException`."""
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
    }.get(status_code, "http_error")


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    log.info(
        "api.error",
        path=request.url.path,
        status=exc.status_code,
        code=exc.code,
    )
    body = error_envelope(exc.code, str(exc.detail)).model_dump()
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Format Starlette/FastAPI ``HTTPException`` consistently with our envelope."""
    if isinstance(exc, ApiError):
        return await api_error_handler(request, exc)
    code = _http_status_to_code(exc.status_code)
    log.info(
        "api.http_exception",
        path=request.url.path,
        status=exc.status_code,
        code=code,
    )
    body = error_envelope(code, str(exc.detail or code)).model_dump()
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic body / query / path validation failure — HTTP 422."""
    log.info("api.validation_error", path=request.url.path)
    body = error_envelope(
        "validation_error",
        "Request validation failed.",
    ).model_dump()
    body["error"]["details"] = exc.errors()
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=_jsonify(body))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort 500 handler.

    Per ``docs/architecture/07-security.md`` §1.4 we **must not** leak
    internal exception detail to the client. We attach an opaque
    ``trace_id`` to the response and the structured log so the operator
    can correlate.
    """
    trace_id = str(uuid.uuid4())
    log.exception(
        "api.unhandled_exception",
        path=request.url.path,
        trace_id=trace_id,
        exc_type=exc.__class__.__name__,
    )
    body = error_envelope(
        "internal_server_error",
        "An unexpected error occurred. Please retry; if it persists, contact support.",
    ).model_dump()
    body["error"]["trace_id"] = trace_id
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Install all error handlers on the given FastAPI application."""
    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)


def _jsonify(value: Any) -> Any:
    """Recursively coerce non-JSON-native objects (bytes, exceptions, …) to str."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonify(v) for v in value]
    if isinstance(value, BaseException):
        return str(value)
    return value


__all__ = [
    "ApiError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "UpstreamError",
    "register_exception_handlers",
]
