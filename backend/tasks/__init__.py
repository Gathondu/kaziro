"""Celery task surface.

Importing :mod:`backend.tasks` registers every Celery task (the
``include`` list in :func:`backend.tasks.celery_app.create_celery_app`
also forces autodiscovery, but importing here keeps in-process callers
— FastAPI handlers, tests — from having to remember the submodule).
"""

from __future__ import annotations

from backend.tasks.celery_app import (
    ALL_QUEUES,
    QUEUE_DEFAULT,
    QUEUE_DOCUMENT,
    QUEUE_EVALUATOR,
    QUEUE_MAINTENANCE,
    QUEUE_PARSER,
    QUEUE_RESEARCH,
    celery_app,
)
from backend.tasks.maintenance import purge_expired_company_summaries
from backend.tasks.pipeline import (
    enqueue_active_pipelines,
    run_document_for_evaluation,
    run_evaluator_for_user,
    run_parser_for_raw_job,
    run_pipeline_for_config_task,
    run_pipeline_for_single_job_task,
    run_research_for_posting,
)

__all__ = [
    "ALL_QUEUES",
    "QUEUE_DEFAULT",
    "QUEUE_DOCUMENT",
    "QUEUE_EVALUATOR",
    "QUEUE_MAINTENANCE",
    "QUEUE_PARSER",
    "QUEUE_RESEARCH",
    "celery_app",
    "enqueue_active_pipelines",
    "purge_expired_company_summaries",
    "run_document_for_evaluation",
    "run_evaluator_for_user",
    "run_parser_for_raw_job",
    "run_pipeline_for_config_task",
    "run_pipeline_for_single_job_task",
    "run_research_for_posting",
]
