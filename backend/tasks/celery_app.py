"""Celery application factory + queue routing.

The worker / beat services in ``docker-compose.yml`` boot from this
module:

    celery -A backend.tasks.celery_app:celery_app worker -Q parser,default
    celery -A backend.tasks.celery_app:celery_app worker -Q evaluator,research,document
    celery -A backend.tasks.celery_app:celery_app beat   --loglevel=info

Tasks are autodiscovered from the modules listed in :data:`TASK_MODULES`.
Per-stage queue routing keeps the heavy LLM-bound stages on dedicated
workers — see ``docs/architecture/06-observability.md`` and PLAN T2.10.
"""

from __future__ import annotations

from typing import Final

from celery import Celery
from celery.schedules import crontab

from backend.config import Settings, get_settings
from backend.services.langsmith_tracing import apply_langsmith_tracing_from_settings

# ---------------------------------------------------------------------------
# Queue definitions
# ---------------------------------------------------------------------------

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

TASK_MODULES: Final[tuple[str, ...]] = (
    "backend.tasks.pipeline",
    "backend.tasks.maintenance",
)

# Map of task name → queue. Tasks not listed here go to QUEUE_DEFAULT.
TASK_ROUTES: Final[dict[str, dict[str, str]]] = {
    "backend.tasks.run_parser_for_raw_job": {"queue": QUEUE_PARSER},
    "backend.tasks.run_evaluator_for_user": {"queue": QUEUE_EVALUATOR},
    "backend.tasks.run_research_for_posting": {"queue": QUEUE_RESEARCH},
    "backend.tasks.run_document_for_evaluation": {"queue": QUEUE_DOCUMENT},
    "backend.tasks.run_pipeline_for_config": {"queue": QUEUE_DEFAULT},
    "backend.tasks.run_pipeline_for_single_job": {"queue": QUEUE_DEFAULT},
    "backend.tasks.enqueue_active_pipelines": {"queue": QUEUE_DEFAULT},
    "backend.tasks.purge_expired_company_summaries": {"queue": QUEUE_MAINTENANCE},
}


def _build_beat_schedule() -> dict[str, dict[str, object]]:
    """Static Beat schedule.

    ``enqueue_active_pipelines`` runs at minute 0 every hour (UTC) and
    enqueues ``run_pipeline_for_config`` only for configs whose preset
    ``fetch_schedule_cron`` matches that tick (daily / weekly). The
    daily cache purge keeps ``company_summaries`` from growing unbounded.
    """
    return {
        "enqueue-active-pipelines-hourly": {
            "task": "backend.tasks.enqueue_active_pipelines",
            "schedule": crontab(minute="0"),
            "options": {"queue": QUEUE_DEFAULT},
        },
        "purge-expired-company-summaries-daily": {
            "task": "backend.tasks.purge_expired_company_summaries",
            "schedule": crontab(minute="15", hour="3"),
            "options": {"queue": QUEUE_MAINTENANCE},
        },
    }


def create_celery_app(settings: Settings | None = None) -> Celery:
    """Build the process-wide :class:`celery.Celery` instance."""
    settings = settings or get_settings()

    app = Celery(
        "kaziro",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            *TASK_MODULES,
            "backend.services.celery_signals",
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
        task_default_queue=QUEUE_DEFAULT,
        task_routes=TASK_ROUTES,
        task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
        task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
        worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
        worker_pool=settings.celery_worker_pool,
        task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
        beat_schedule=_build_beat_schedule(),
    )

    apply_langsmith_tracing_from_settings(settings)

    return app


celery_app: Final[Celery] = create_celery_app()

__all__ = [
    "ALL_QUEUES",
    "QUEUE_DEFAULT",
    "QUEUE_DOCUMENT",
    "QUEUE_EVALUATOR",
    "QUEUE_MAINTENANCE",
    "QUEUE_PARSER",
    "QUEUE_RESEARCH",
    "TASK_MODULES",
    "TASK_ROUTES",
    "celery_app",
    "create_celery_app",
]
