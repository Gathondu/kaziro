from __future__ import annotations

from config.celery import celery_app


@celery_app.task(name="apps.pipeline.healthcheck")
def healthcheck() -> str:
    return "ok"
