from __future__ import annotations

import uuid
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError, ValidationError

from apps.core.schemas import error_envelope
from config.logging import get_logger

log = get_logger(__name__)


class ApiError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class BadRequestError(ApiError):
    status_code = 400
    code = "bad_request"


class UnauthorizedError(ApiError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(ApiError):
    status_code = 403
    code = "forbidden"


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


class ConflictError(ApiError):
    status_code = 409
    code = "conflict"


class UpstreamError(ApiError):
    status_code = 502
    code = "upstream_error"


def _json_response(code: str, message: str, status_code: int, **extra: Any) -> JsonResponse:
    body = error_envelope(code, message, **extra)
    return JsonResponse(body, status=status_code)


def api_error_handler(request: HttpRequest, exc: ApiError) -> JsonResponse:
    log.info("api.error", path=request.path, status_code=exc.status_code, code=exc.code)
    return _json_response(exc.code, exc.message, exc.status_code)


def authentication_error_handler(request: HttpRequest, _exc: AuthenticationError) -> JsonResponse:
    log.info("api.auth_error", path=request.path, status_code=401, code="unauthorized")
    return _json_response("unauthorized", "Authentication credentials were not provided.", 401)


def validation_error_handler(request: HttpRequest, exc: ValidationError) -> JsonResponse:
    details = getattr(exc, "errors", None)
    if callable(details):
        details = details()
    if not isinstance(details, list):
        details = None
    log.info("api.validation_error", path=request.path, status_code=422)
    return _json_response(
        "validation_error",
        "Request validation failed.",
        422,
        details=details,
    )


def http_error_handler(request: HttpRequest, exc: HttpError) -> JsonResponse:
    code = "http_error" if exc.status_code >= 500 else "bad_request"
    if exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 401:
        code = "unauthorized"
    elif exc.status_code == 403:
        code = "forbidden"
    elif exc.status_code == 409:
        code = "conflict"
    log.info("api.http_error", path=request.path, status_code=exc.status_code, code=code)
    return _json_response(code, str(exc), exc.status_code)


def django_not_found_handler(request: HttpRequest, _exc: Http404) -> JsonResponse:
    return _json_response("not_found", "Resource not found.", 404)


def permission_denied_handler(request: HttpRequest, _exc: PermissionDenied) -> JsonResponse:
    return _json_response("forbidden", "You do not have permission to perform this action.", 403)


def unhandled_exception_handler(request: HttpRequest, exc: Exception) -> JsonResponse:
    trace_id = str(uuid.uuid4())
    log.exception(
        "api.unhandled_exception",
        path=request.path,
        trace_id=trace_id,
        exc_type=exc.__class__.__name__,
    )
    return _json_response(
        "internal_server_error",
        "An unexpected error occurred. Please retry; if it persists, contact support.",
        500,
        trace_id=trace_id,
    )


def register_exception_handlers(api: NinjaAPI) -> None:
    api.add_exception_handler(ApiError, api_error_handler)  # type: ignore
    api.add_exception_handler(AuthenticationError, authentication_error_handler)  # type: ignore
    api.add_exception_handler(ValidationError, validation_error_handler)  # type: ignore
    api.add_exception_handler(HttpError, http_error_handler)  # type: ignore
    api.add_exception_handler(Http404, django_not_found_handler)  # type: ignore
    api.add_exception_handler(PermissionDenied, permission_denied_handler)  # type: ignore
    api.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore


__all__ = [
    "ApiError",
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "UpstreamError",
    "register_exception_handlers",
]
