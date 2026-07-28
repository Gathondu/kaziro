"""Celery task surface for the Kaziro agentic pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apps.jobs import fetcher, repositories
from apps.jobs.models import (
    FETCH_CRON_DAILY,
    FETCH_CRON_WEEKLY,
    EvaluationClassification,
    JobEvaluation,
    JobSearchConfig,
)
from apps.notifications.tasks import create_notification_task
from apps.pipeline.document_agent import run_document_agent
from apps.pipeline.evaluator_agent import run_evaluator_agent
from apps.pipeline.parser_agent import run_parser_agent
from apps.pipeline.research_agent import run_research_agent
from config.celery import (
    QUEUE_DEFAULT,
    QUEUE_DOCUMENT,
    QUEUE_EVALUATOR,
    QUEUE_PARSER,
    QUEUE_RESEARCH,
    app,
    run_async,
)
from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)
settings = get_settings()


@app.task(name="apps.pipeline.healthcheck")
def healthcheck() -> str:
    return "ok"


@app.task(
    name="apps.pipeline.run_pipeline_for_config",
    queue=QUEUE_DEFAULT,
    **settings.CELERY_RETRY_KWARGS,
)
def run_pipeline_for_config(config_id: str, user_id: str) -> dict[str, object]:
    return run_async(lambda: _run_pipeline_for_config(config_id, user_id))


@app.task(name="apps.pipeline.run_parser", queue=QUEUE_PARSER)
def run_parser_for_raw_job(raw_job_id: str) -> dict[str, object]:
    return run_async(lambda: run_parser_agent(raw_job_id)).model_dump(mode="json")


@app.task(name="apps.pipeline.run_evaluator", queue=QUEUE_EVALUATOR)
def run_evaluator_for_user(job_posting_id: str, user_id: str) -> dict[str, object]:
    return run_async(lambda: run_evaluator_agent(job_posting_id, user_id)).model_dump(mode="json")


@app.task(name="apps.pipeline.run_research", queue=QUEUE_RESEARCH)
def run_research_for_posting(job_posting_id: str) -> dict[str, object]:
    return run_async(lambda: run_research_agent(job_posting_id)).model_dump(mode="json")


@app.task(name="apps.pipeline.run_document", queue=QUEUE_DOCUMENT)
def run_document_for_evaluation(
    evaluation_id: str,
    user_id: str,
    regenerate_scope: str = "all",
) -> dict[str, object]:
    return run_async(
        lambda: run_document_agent(evaluation_id, user_id, regenerate_scope)
    ).model_dump(mode="json")


@app.task(
    name="apps.pipeline.run_single_job_pipeline",
    queue=QUEUE_DEFAULT,
    **settings.CELERY_RETRY_KWARGS,
)
def run_single_job_pipeline(raw_job_id: str, user_id: str) -> dict[str, object]:
    return run_async(lambda: _run_single_job_pipeline(raw_job_id, user_id))


@app.task(name="apps.pipeline.enqueue_active_pipelines", queue=QUEUE_DEFAULT)
def enqueue_active_pipelines() -> dict[str, int]:
    return run_async(_enqueue_active_pipelines)


async def _run_pipeline_for_config(config_id: str, user_id: str) -> dict[str, object]:
    bound = log.bind(job_config_id=config_id, user_id=user_id, stage="pipeline")
    bound.info("pipeline.start")
    config = await repositories.get_for_user_id(user_id, config_id)
    if config is None:
        raise ValueError("Job config not found.")
    raw_jobs = await fetcher.fetch_jobs_for_config(config)
    summary: dict[str, Any] = {
        "config_id": config_id,
        "user_id": user_id,
        "jobs_fetched": len(raw_jobs),
        "jobs_parsed": 0,
        "jobs_evaluated": 0,
        "jobs_researched": 0,
        "documents_generated": 0,
        "errors": [],
    }
    for raw_job in raw_jobs:
        parsed = await run_parser_agent(str(raw_job.id))
        if parsed.error or not parsed.job_posting_id:
            summary["errors"].append(parsed.error or "Parser returned no posting")
            continue
        summary["jobs_parsed"] += 1
        evaluated = await run_evaluator_agent(parsed.job_posting_id, user_id)
        if evaluated.error or not evaluated.evaluation_id:
            summary["errors"].append(evaluated.error or "Evaluator returned no evaluation")
            continue
        summary["jobs_evaluated"] += 1
        if evaluated.classification != EvaluationClassification.GOOD_FIT:
            continue
        research = await run_research_agent(parsed.job_posting_id)
        if research.error or not research.summary_id:
            summary["errors"].append(research.error or "Research returned no summary")
            continue
        summary["jobs_researched"] += 1
        document = await run_document_agent(evaluated.evaluation_id, user_id)
        if document.error or not document.document_id:
            summary["errors"].append(document.error or "Document generation returned no document")
            continue
        summary["documents_generated"] += 1

    create_notification_task.delay(
        config.user.id,
        "pipeline_failed" if summary["errors"] else "pipeline_completed",
        "Job search completed with errors" if summary["errors"] else "Job search completed",
        (
            f"Found {summary['jobs_fetched']} new jobs and prepared "
            f"{summary['documents_generated']} application packs. "
            f"{len(summary['errors'])} stage failures were recorded."
        ),
        summary,
    )
    bound.info(
        "pipeline.complete",
        jobs_fetched=summary["jobs_fetched"],
        jobs_parsed=summary["jobs_parsed"],
        jobs_evaluated=summary["jobs_evaluated"],
        errors=len(summary["errors"]),
    )
    return summary


async def _run_single_job_pipeline(raw_job_id: str, user_id: str) -> dict[str, object]:
    summary: dict[str, object] = {
        "raw_job_id": raw_job_id,
        "user_id": user_id,
        "parsed": False,
        "evaluated": False,
        "researched": False,
        "documents_generated": False,
        "errors": [],
    }
    errors = summary["errors"]
    assert isinstance(errors, list)
    parsed = await run_parser_agent(raw_job_id)
    if parsed.error or not parsed.job_posting_id:
        errors.append(parsed.error or "Parser returned no posting")
        _queue_single_notification(user_id, summary, errors)
        return summary
    summary["parsed"] = True
    evaluated = await run_evaluator_agent(parsed.job_posting_id, user_id)
    if evaluated.error or not evaluated.evaluation_id:
        errors.append(evaluated.error or "Evaluator returned no evaluation")
        _queue_single_notification(user_id, summary, errors)
        return summary
    summary["evaluated"] = True
    if evaluated.classification == EvaluationClassification.GOOD_FIT:
        research = await run_research_agent(parsed.job_posting_id)
        if research.error or not research.summary_id:
            errors.append(research.error or "Research returned no summary")
        else:
            summary["researched"] = True
            document = await run_document_agent(evaluated.evaluation_id, user_id)
            if document.error or not document.document_id:
                errors.append(document.error or "Document generation returned no document")
            else:
                summary["documents_generated"] = True
    _queue_single_notification(user_id, summary, errors)
    return summary


def _queue_single_notification(
    user_id: str,
    summary: dict[str, object],
    errors: list[object],
) -> None:
    create_notification_task.delay(
        user_id,
        "job_import_failed" if errors else "job_import_completed",
        "Imported job needs attention" if errors else "Imported job processed",
        (
            "The imported job could not complete every processing stage."
            if errors
            else "Your imported job is ready to review."
        ),
        summary,
    )


async def _enqueue_active_pipelines() -> dict[str, int]:
    now = datetime.now(UTC)
    queued = 0
    skipped = 0
    queryset = JobSearchConfig.objects.select_related("user").filter(
        is_active=True,
        user__is_active=True,
    )
    async for config in queryset:
        if _should_run(config.fetch_schedule_cron, now):
            run_pipeline_for_config.delay(str(config.id), str(config.user.id))
            queued += 1
        else:
            skipped += 1
    log.info("pipeline.scheduler.complete", queued=queued, skipped=skipped)
    return {"queued": queued, "skipped": skipped}


def _should_run(cron: str, now: datetime) -> bool:
    if cron == FETCH_CRON_DAILY:
        return now.hour == 6
    if cron == FETCH_CRON_WEEKLY:
        return now.hour == 6 and now.weekday() == 0
    return False


async def regenerate_documents(
    job_posting_id: str,
    user_id: str,
    scope: str = "all",
) -> str:
    evaluation = await JobEvaluation.objects.filter(
        job_posting_id=uuid.UUID(job_posting_id),
        user_id=user_id,
        final_classification=EvaluationClassification.GOOD_FIT,
    ).afirst()
    if evaluation is None:
        raise ValueError("A GOOD_FIT evaluation is required.")
    result = run_document_for_evaluation.delay(str(evaluation.id), user_id, scope)
    return result.id


__all__ = [
    "enqueue_active_pipelines",
    "healthcheck",
    "regenerate_documents",
    "run_document_for_evaluation",
    "run_evaluator_for_user",
    "run_parser_for_raw_job",
    "run_pipeline_for_config",
    "run_research_for_posting",
    "run_single_job_pipeline",
]
