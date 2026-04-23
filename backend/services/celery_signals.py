"""Celery worker signal hooks (request-id propagation, logging context)."""

from __future__ import annotations

from typing import Any

import structlog
from celery import signals

from backend.logging_config import get_logger

log = get_logger(__name__)


@signals.task_prerun.connect
def _bind_request_id(
    sender: Any = None,
    task_id: str | None = None,
    task: Any = None,
    **kwargs: Any,
) -> None:
    request_id = ""
    try:
        req = getattr(task, "request", None)
        headers = getattr(req, "headers", None) if req is not None else None
        if isinstance(headers, dict):
            rid = headers.get("request_id")
            if isinstance(rid, str):
                request_id = rid
    except Exception:
        log.warning("celery.request_id_read_failed", task_id=task_id, exc_info=True)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        celery_task_id=task_id or "",
        request_id=request_id or None,
    )


@signals.task_postrun.connect
def _clear_context(**_kwargs: Any) -> None:
    structlog.contextvars.clear_contextvars()


# Importing this module registers the handlers via decorators.
__all__: list[str] = []
