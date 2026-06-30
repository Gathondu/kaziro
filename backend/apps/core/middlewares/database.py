from __future__ import annotations

import time
from collections.abc import Callable

from django.db import connection
from django.http import HttpRequest, HttpResponse

from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)


class DatabaseQueryLoggerMiddleware:
    """Instruments the Django database connection to intercept and log slow SQL statements."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        settings = get_settings()
        threshold = settings.SLOW_QUERY_THRESHOLD_MS

        def query_wrapper(execute, sql, params, many, context):
            start_time = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if duration_ms >= threshold:
                    log.warning(
                        "db.query.slow",
                        duration_ms=duration_ms,
                        sql=str(sql).strip().replace("\n", " "),
                    )

        with connection.execute_wrapper(query_wrapper):
            return self.get_response(request)


__all__ = ["DatabaseQueryLoggerMiddleware"]
