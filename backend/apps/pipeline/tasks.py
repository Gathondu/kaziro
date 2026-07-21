from __future__ import annotations

from apps.jobs import fetcher, repositories
from apps.notifications.tasks import create_notification_task
from config.celery import QUEUE_DEFAULT, app, run_async
from config.logging import get_logger

log = get_logger(__name__)


@app.task(name="apps.pipeline.healthcheck")
def healthcheck() -> str:
    return "ok"


@app.task(name="apps.pipeline.run_pipeline_for_config", queue=QUEUE_DEFAULT)
def run_pipeline_for_config(config_id: str, user_id: str) -> dict[str, object]:
    return run_async(lambda: _run_pipeline_for_config(config_id, user_id))


async def _run_pipeline_for_config(config_id: str, user_id: str) -> dict[str, object]:
    config = await repositories.get_for_user_id(user_id, config_id)
    if config is None:
        raise ValueError("Job config not found.")
    raw_jobs = await fetcher.fetch_jobs_for_config(config)
    create_notification_task.delay(
        config.user.id,
        "job_config_queued",
        "Job search queued",
        f"Fetched {len(raw_jobs)} new raw jobs for parsing.",
        {"config_id": str(config.id), "raw_jobs": len(raw_jobs)},
    )
    log.info(
        "pipeline.fetch_completed",
        job_config_id=str(config.id),
        user_id=user_id,
        jobs_fetched=len(raw_jobs),
    )
    return {
        "config_id": str(config.id),
        "user_id": user_id,
        "jobs_fetched": len(raw_jobs),
        "jobs_parsed": 0,
        "errors": [],
    }
