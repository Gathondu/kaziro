from __future__ import annotations

from django.db import connections
from django.db.utils import DatabaseError
from django.http import HttpRequest, JsonResponse

from apps.core.schemas import envelope, error_envelope
from config.logging import get_logger

log = get_logger(__name__)


def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse(envelope({"status": "ok"}))


def readiness(_request: HttpRequest) -> JsonResponse:
    try:
        connections["default"].cursor().execute("SELECT 1")
    except DatabaseError:
        log.error("health.readiness.database_unavailable", exc_info=True)
        return JsonResponse(
            error_envelope("database_unavailable", "Database readiness check failed."), status=503
        )
    return JsonResponse(envelope({"status": "ready", "database": "ok"}))
