from __future__ import annotations

from django.db import connections
from django.db.utils import DatabaseError
from django.http import JsonResponse


def health(_request) -> JsonResponse:
    return JsonResponse({"data": {"status": "ok"}, "meta": None, "error": None})


def readiness(_request) -> JsonResponse:
    try:
        connections["default"].cursor().execute("SELECT 1")
    except DatabaseError:
        return JsonResponse(
            {
                "data": {"status": "unavailable", "database": "error"},
                "meta": None,
                "error": {
                    "code": "database_unavailable",
                    "message": "Database readiness check failed.",
                },
            },
            status=503,
        )
    return JsonResponse({"data": {"status": "ready", "database": "ok"}, "meta": None, "error": None})
