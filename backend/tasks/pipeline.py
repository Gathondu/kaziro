"""Celery tasks that drive the agentic pipeline.

Tasks are thin sync wrappers over the async agents/orchestrator. They
exist so Celery Beat can schedule periodic runs and so the API can
enqueue manual triggers without blocking the request thread.

Public task names (must stay stable — they appear on the broker):

* ``backend.tasks.run_pipeline_for_config``
* ``backend.tasks.run_pipeline_for_single_job``
* ``backend.tasks.run_parser_for_raw_job``
* ``backend.tasks.run_evaluator_for_user``
* ``backend.tasks.run_research_for_posting``
* ``backend.tasks.run_document_for_evaluation``
* ``backend.tasks.enqueue_active_pipelines`` (Beat fan-out; per-config schedule gate)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from celery import shared_task

from backend.agents.document_agent import run_document_agent
from backend.agents.evaluator_agent import run_evaluator_agent
from backend.agents.parser_agent import run_parser_agent
from backend.agents.pipeline_orchestrator import (
    run_full_pipeline_for_config,
    run_pipeline_for_single_job,
)
from backend.agents.research_agent import run_research_agent
from backend.db.repositories import job_config_repository
from backend.db.session import async_session_factory
from backend.logging_config import get_logger
from backend.services.schedule_presets import (
    ALLOWED_FETCH_SCHEDULE_CRONS,
    should_run_fetch,
)
from backend.tasks.celery_app import (
    QUEUE_DEFAULT,
    QUEUE_DOCUMENT,
    QUEUE_EVALUATOR,
    QUEUE_PARSER,
    QUEUE_RESEARCH,
)

log = get_logger(__name__)

# Standard retry policy for pipeline tasks. Three attempts with
# exponential backoff (60s, 120s, 240s ± jitter).
_RETRY_KWARGS: Final[dict[str, Any]] = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 600,
    "retry_jitter": True,
    "max_retries": 3,
}


# ---------------------------------------------------------------------------
# Per-stage tasks
# ---------------------------------------------------------------------------


@shared_task(
    name="backend.tasks.run_parser_for_raw_job",
    queue=QUEUE_PARSER,
    bind=True,
    **_RETRY_KWARGS,
)
def run_parser_for_raw_job(self: Any, raw_job_id: str) -> dict[str, Any]:
    """Parse one ``raw_jobs`` row by id."""
    log.info(
        "tasks.parser_start",
        raw_job_id=raw_job_id,
        attempt=self.request.retries + 1,
    )

    from backend.db.models.raw_job import RawJob

    async def _runner() -> dict[str, Any]:
        async with async_session_factory() as session:
            raw = await session.get(RawJob, uuid.UUID(raw_job_id))
        if raw is None:
            return {"raw_job_id": raw_job_id, "error": "raw_job not found"}
        result = await run_parser_agent(raw_job_id, raw.raw_payload)
        return {
            "raw_job_id": raw_job_id,
            "job_posting_id": result.job_posting_id,
            "error": result.error,
        }

    return asyncio.run(_runner())


@shared_task(
    name="backend.tasks.run_evaluator_for_user",
    queue=QUEUE_EVALUATOR,
    bind=True,
    **_RETRY_KWARGS,
)
def run_evaluator_for_user(
    self: Any, job_posting_id: str, user_id: str
) -> dict[str, Any]:
    log.info(
        "tasks.evaluator_start",
        job_posting_id=job_posting_id,
        user_id=user_id,
        attempt=self.request.retries + 1,
    )
    result = asyncio.run(run_evaluator_agent(job_posting_id, user_id))
    return {
        "job_posting_id": job_posting_id,
        "user_id": user_id,
        "evaluation_id": result.job_evaluation_id,
        "classification": (
            result.final_classification.value
            if result.final_classification
            else None
        ),
        "overall_score": result.overall_score,
        "error": result.error,
    }


@shared_task(
    name="backend.tasks.run_research_for_posting",
    queue=QUEUE_RESEARCH,
    bind=True,
    **_RETRY_KWARGS,
)
def run_research_for_posting(self: Any, job_posting_id: str) -> dict[str, Any]:
    log.info(
        "tasks.research_start",
        job_posting_id=job_posting_id,
        attempt=self.request.retries + 1,
    )
    result = asyncio.run(run_research_agent(job_posting_id))
    return {
        "job_posting_id": job_posting_id,
        "summary_id": result.summary_id,
        "skipped": result.skipped,
        "error": result.error,
    }


@shared_task(
    name="backend.tasks.run_document_for_evaluation",
    queue=QUEUE_DOCUMENT,
    bind=True,
    **_RETRY_KWARGS,
)
def run_document_for_evaluation(
    self: Any, job_evaluation_id: str, user_id: str
) -> dict[str, Any]:
    log.info(
        "tasks.document_start",
        job_evaluation_id=job_evaluation_id,
        user_id=user_id,
        attempt=self.request.retries + 1,
    )
    result = asyncio.run(run_document_agent(job_evaluation_id, user_id))
    return {
        "job_evaluation_id": job_evaluation_id,
        "user_id": user_id,
        "application_doc_id": result.application_doc_id,
        "quality_passed": result.quality_passed,
        "error": result.error,
    }


# ---------------------------------------------------------------------------
# Whole-pipeline tasks
# ---------------------------------------------------------------------------


@shared_task(
    name="backend.tasks.run_pipeline_for_config",
    queue=QUEUE_DEFAULT,
    bind=True,
    **_RETRY_KWARGS,
)
def run_pipeline_for_config_task(
    self: Any, config_id: str, user_id: str
) -> dict[str, Any]:
    """Run fetch → parse → evaluate → research → document for one config."""
    log.info(
        "tasks.pipeline_full_start",
        config_id=config_id,
        user_id=user_id,
        attempt=self.request.retries + 1,
    )
    return asyncio.run(run_full_pipeline_for_config(config_id, user_id))


@shared_task(
    name="backend.tasks.run_pipeline_for_single_job",
    queue=QUEUE_DEFAULT,
    bind=True,
    **_RETRY_KWARGS,
)
def run_pipeline_for_single_job_task(
    self: Any, job_posting_id: str, user_id: str
) -> dict[str, Any]:
    """Manual one-job trigger from the API."""
    log.info(
        "tasks.pipeline_single_start",
        job_posting_id=job_posting_id,
        user_id=user_id,
        attempt=self.request.retries + 1,
    )
    return asyncio.run(run_pipeline_for_single_job(job_posting_id, user_id))


# ---------------------------------------------------------------------------
# Beat fan-out
# ---------------------------------------------------------------------------


@shared_task(
    name="backend.tasks.enqueue_active_pipelines",
    queue=QUEUE_DEFAULT,
    bind=True,
)
def enqueue_active_pipelines(self: Any) -> dict[str, Any]:
    """Beat target: enqueue ``run_pipeline_for_config`` for due configs only.

    Beat fires at minute 0 every hour (UTC). Each active config's
    ``fetch_schedule_cron`` must be one of two preset strings; this task
    enqueues only when ``should_run_fetch`` matches the current tick.
    """

    async def _list_active() -> list[tuple[str, str, str]]:
        async with async_session_factory() as session:
            configs = await job_config_repository.list_active_for_scheduler(
                session
            )
        return [(str(c.id), str(c.user_id), c.fetch_schedule_cron) for c in configs]

    rows = asyncio.run(_list_active())
    now = datetime.now(UTC)
    task_id = getattr(self.request, "id", None)
    task_log = get_logger(__name__).bind(task_id=task_id or "")
    pairs: list[tuple[str, str]] = []
    skipped = 0
    for config_id, user_id, cron in rows:
        if cron not in ALLOWED_FETCH_SCHEDULE_CRONS:
            task_log.warning(
                "tasks.enqueue_active_pipelines_unknown_cron",
                config_id=config_id,
                fetch_schedule_cron=cron,
            )
            skipped += 1
            continue
        if should_run_fetch(cron, now):
            pairs.append((config_id, user_id))
        else:
            skipped += 1
    for config_id, user_id in pairs:
        run_pipeline_for_config_task.delay(config_id, user_id)

    task_log.info(
        "tasks.enqueue_active_pipelines_done",
        enqueued=len(pairs),
        skipped=skipped,
    )
    return {"enqueued": len(pairs), "skipped": skipped}


__all__ = [
    "enqueue_active_pipelines",
    "run_document_for_evaluation",
    "run_evaluator_for_user",
    "run_parser_for_raw_job",
    "run_pipeline_for_config_task",
    "run_pipeline_for_single_job_task",
    "run_research_for_posting",
]
