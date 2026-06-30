from __future__ import annotations

from config.celery import app


@app.task(name="apps.pipeline.healthcheck")
def healthcheck() -> str:
    return "ok"
