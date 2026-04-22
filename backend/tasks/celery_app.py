"""Celery application factory.

This is intentionally minimal in Phase 0 — just enough wiring so the
``worker`` and ``beat`` services in ``docker-compose.yml`` can boot and
report healthy. Phase 3 (T3.1+) extends this with task modules,
beat schedules, and queue routing.

Usage::

    celery -A backend.tasks.celery_app:celery_app worker --loglevel=info
    celery -A backend.tasks.celery_app:celery_app beat   --loglevel=info
"""

from __future__ import annotations

from typing import Final

from celery import Celery

from backend.config import Settings, get_settings


def create_celery_app(settings: Settings | None = None) -> Celery:
    """Build the process-wide :class:`celery.Celery` instance."""
    settings = settings or get_settings()

    app = Celery(
        "kaziro",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            # Future task modules registered here:
            # "backend.tasks.pipeline",
            # "backend.tasks.notifications",
        ],
    )

    app.conf.update(
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

    return app


celery_app: Final[Celery] = create_celery_app()


__all__ = ["celery_app", "create_celery_app"]
