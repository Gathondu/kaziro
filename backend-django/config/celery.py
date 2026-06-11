"""Celery app for the parallel Kaziro Django backend."""

from __future__ import annotations

import os
from typing import Final

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

QUEUE_DEFAULT: Final[str] = "default"
QUEUE_PARSER: Final[str] = "parser"
QUEUE_EVALUATOR: Final[str] = "evaluator"
QUEUE_RESEARCH: Final[str] = "research"
QUEUE_DOCUMENT: Final[str] = "document"
QUEUE_MAINTENANCE: Final[str] = "maintenance"

ALL_QUEUES: Final[tuple[str, ...]] = (
    QUEUE_DEFAULT,
    QUEUE_PARSER,
    QUEUE_EVALUATOR,
    QUEUE_RESEARCH,
    QUEUE_DOCUMENT,
    QUEUE_MAINTENANCE,
)

celery_app = Celery("kaziro_django")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.conf.update(
    task_default_queue=QUEUE_DEFAULT,
    task_routes={},
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

__all__ = [
    "ALL_QUEUES",
    "QUEUE_DEFAULT",
    "QUEUE_DOCUMENT",
    "QUEUE_EVALUATOR",
    "QUEUE_MAINTENANCE",
    "QUEUE_PARSER",
    "QUEUE_RESEARCH",
    "celery_app",
]
