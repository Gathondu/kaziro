"""Celery app for the Kaziro Django backend."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Coroutine
from threading import Thread
from typing import Any, Final

from celery import Celery
from django.db import connections

from config.langsmith import apply_langsmith_from_settings
from config.logging import configure_logging
from config.settings import get_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

configure_logging()

settings = get_settings()
apply_langsmith_from_settings(settings)

QUEUE_DEFAULT: Final[str] = "default"
QUEUE_PARSER: Final[str] = "parser"
QUEUE_EVALUATOR: Final[str] = "evaluator"
QUEUE_RESEARCH: Final[str] = "research"
QUEUE_DOCUMENT: Final[str] = "document"
QUEUE_MAINTENANCE: Final[str] = "maintenance"
QUEUE_NOTIFICATION: Final[str] = "notification"

ALL_QUEUES: Final[tuple[str, ...]] = (
    QUEUE_DEFAULT,
    QUEUE_PARSER,
    QUEUE_EVALUATOR,
    QUEUE_RESEARCH,
    QUEUE_DOCUMENT,
    QUEUE_MAINTENANCE,
    QUEUE_NOTIFICATION,
)


def run_async[T](factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    result: dict[str, T] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(factory())
        except BaseException as exc:  # pragma: no cover - re-raised in caller
            error["value"] = exc
        finally:
            connections.close_all()

    thread = Thread(target=_runner)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result["value"]


celery_app = Celery("kaziro_django")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.conf.update(
    task_default_queue=QUEUE_DEFAULT,
    # task_routes=TASK_ROUTES,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks()
app = celery_app

__all__ = [
    "ALL_QUEUES",
    "QUEUE_DEFAULT",
    "QUEUE_DOCUMENT",
    "QUEUE_EVALUATOR",
    "QUEUE_MAINTENANCE",
    "QUEUE_NOTIFICATION",
    "QUEUE_PARSER",
    "QUEUE_RESEARCH",
    "app",
    "celery_app",
    "run_async",
]
