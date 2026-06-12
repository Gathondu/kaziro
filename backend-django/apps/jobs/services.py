from __future__ import annotations

from apps.accounts.models import User
from apps.core.exceptions import NotFoundError
from apps.core.logging_config import get_logger
from apps.jobs import repositories
from apps.jobs.models import JobSearchConfig
from apps.jobs.schemas import (
    JobConfigPayload,
    JobConfigResponse,
    RunConfigResponse,
    schedule_presets,
)
from apps.notifications.services import create_notification
from apps.notifications.tasks import create_notification_task

log = get_logger(__name__)


async def list_configs(user: User) -> list[JobConfigResponse]:
    return [to_response(config) for config in await repositories.list_for_user(user)]


async def create_config(user: User, payload: JobConfigPayload) -> JobConfigResponse:
    config = await repositories.create_for_user(
        user,
        name=payload.name or "",
        keywords=_clean_list(payload.keywords),
        location=payload.location or "",
        remote_only=payload.remote_only,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        employment_types=_clean_list(payload.employment_types),
        fetch_schedule_cron=payload.fetch_schedule_cron,
        is_active=payload.is_active,
    )
    log.info("job_config.created", user_id=str(user.id), job_config_id=str(config.id))
    return to_response(config)


async def run_config(user: User, config_id: str) -> RunConfigResponse:
    config = await repositories.get_for_user(user, config_id)
    if config is None:
        raise NotFoundError("Job config not found.", code="job_config_not_found")
    task_id = await _enqueue_notification(user, config)
    log.info("job_config.run_enqueued", user_id=str(user.id), job_config_id=str(config.id))
    return RunConfigResponse(task_id=task_id)


def to_response(config: JobSearchConfig) -> JobConfigResponse:
    return JobConfigResponse(
        id=config.id,
        user_id=config.user_id, # type: ignore
        name=config.name or None,
        keywords=config.keywords or [],
        location=config.location or None,
        remote_only=config.remote_only,
        salary_min=config.salary_min,
        salary_max=config.salary_max,
        employment_types=config.employment_types or [],
        fetch_schedule_cron=config.fetch_schedule_cron,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


async def _enqueue_notification(user: User, config: JobSearchConfig) -> str:
    args = (
        str(user.id),
        "fetch_queued",
        "First job search queued",
        "Kaziro will notify you when matching roles are ready.",
        {"type": "fetch_queued", "config_id": config.id},
    )
    try:
        return str(object=await create_notification_task.delay(*args).id)
    except Exception:
        log.warning("job_config.run_enqueue_failed", user_id=str(user.id), exc_info=True)
        notification = await create_notification(
            user=user,
            event_type=args[1],
            title=args[2],
            body=args[3],
            payload=args[4],
        )
        return str(notification.id)


def _clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


__all__ = ["create_config", "list_configs", "run_config", "schedule_presets", "to_response"]
