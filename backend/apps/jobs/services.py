from __future__ import annotations

from apps.accounts.models import User
from apps.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from apps.jobs import repositories
from apps.jobs.models import (
    DraftStatus,
    JobSearchConfig,
    JobSourceConfigDraft,
    JobSourceProvider,
)
from apps.jobs.schemas import (
    DiscoveryRequestPayload,
    JobConfigPayload,
    JobConfigResponse,
    JobSourceConfigDraftResponse,
    JobSourceProviderPayload,
    JobSourceProviderResponse,
    JobSourceValidationRunResponse,
    RunConfigResponse,
    schedule_presets,
)
from apps.jobs.tasks import (
    approve_draft,
    discover_provider_task,
    validate_provider_draft_task,
)
from apps.notifications.services import create_notification
from apps.notifications.tasks import create_notification_task
from apps.pipeline.tasks import run_pipeline_for_config
from config.logging import get_logger

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
    log.info(
        "job_config.created",
        user_id=str(user.id),
        job_config_id=str(config.id),
    )
    return to_response(config)


async def run_config(user: User, config_id: str) -> RunConfigResponse:
    config = await repositories.get_for_user(user, config_id)
    if config is None:
        raise NotFoundError("Job config not found.", code="job_config_not_found")
    task_id = await _enqueue_pipeline(user, config)
    log.info(
        "job_config.run_enqueued",
        user_id=str(user.id),
        job_config_id=str(config.id),
    )
    return RunConfigResponse(task_id=task_id)


async def update_config(
    user: User,
    config_id: str,
    payload: JobConfigPayload,
) -> JobConfigResponse:
    config = await repositories.update_for_user(
        user,
        config_id,
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
    if config is None:
        raise NotFoundError("Job config not found.", code="job_config_not_found")
    return to_response(config)


async def disable_config(user: User, config_id: str) -> JobConfigResponse:
    config = await repositories.update_for_user(user, config_id, is_active=False)
    if config is None:
        raise NotFoundError("Job config not found.", code="job_config_not_found")
    return to_response(config)


async def list_providers(user: User) -> list[JobSourceProviderResponse]:
    _require_staff(user)
    return [provider_to_response(provider) for provider in await repositories.list_providers()]


async def create_provider(
    user: User,
    payload: JobSourceProviderPayload,
) -> JobSourceProviderResponse:
    _require_staff(user)
    provider = await repositories.create_provider(
        slug=payload.slug,
        display_name=payload.display_name,
        docs_url=str(payload.docs_url),
        robots_notes=payload.robots_notes,
        terms_notes=payload.terms_notes,
    )
    log.info(
        "job_source.provider_created",
        provider_id=str(provider.id),
        slug=provider.slug,
    )
    return provider_to_response(provider)


async def trigger_discovery(
    user: User,
    provider_id: str,
    payload: DiscoveryRequestPayload,
) -> RunConfigResponse:
    _require_staff(user)
    provider = await repositories.get_provider(provider_id)
    if provider is None:
        raise NotFoundError("Provider not found.", code="job_source_provider_not_found")
    run = await repositories.create_discovery_run(
        provider,
        known_auth_type=payload.known_auth_type,
        keywords=payload.keywords,
    )
    task = discover_provider_task.delay(
        str(provider.id),
        str(run.id),
        payload.known_auth_type,
        payload.keywords,
    )
    return RunConfigResponse(task_id=task.id)


async def list_provider_drafts(
    user: User,
    provider_id: str,
) -> list[JobSourceConfigDraftResponse]:
    _require_staff(user)
    provider = await repositories.get_provider(provider_id)
    if provider is None:
        raise NotFoundError("Provider not found.", code="job_source_provider_not_found")
    return [draft_to_response(draft) for draft in await repositories.list_drafts(provider)]


async def validate_draft(user: User, draft_id: str) -> RunConfigResponse:
    _require_staff(user)
    draft = await repositories.get_draft(draft_id)
    if draft is None:
        raise NotFoundError("Draft not found.", code="job_source_draft_not_found")
    task = validate_provider_draft_task.delay(str(draft.id))
    return RunConfigResponse(task_id=task.id)


async def approve_config_draft(user: User, draft_id: str) -> JobSourceConfigDraftResponse:
    _require_staff(user)
    draft = await repositories.get_draft(draft_id)
    if draft is None:
        raise NotFoundError("Draft not found.", code="job_source_draft_not_found")
    if draft.status != DraftStatus.VALIDATED:
        raise BadRequestError(
            "Only validated drafts can be approved.",
            code="job_source_draft_not_validated",
        )
    await approve_draft(str(draft.id))
    refreshed = await repositories.get_draft(draft_id)
    if refreshed is None:
        raise NotFoundError("Draft not found.", code="job_source_draft_not_found")
    return draft_to_response(refreshed)


def to_response(config: JobSearchConfig) -> JobConfigResponse:
    return JobConfigResponse(
        id=config.id,
        user_id=config.user_id,  # type: ignore
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
        user.id,
        "job_config_queued",
        "Job search queued",
        "You will be notified when matching roles are ready.",
        {"config_id": str(config.id)},
    )
    try:
        return create_notification_task.delay(*args).id
    except Exception:
        log.warning(
            "job_config.enqueue_notification_failed",
            user_id=str(user.id),
            exc_info=True,
        )
        notification = await create_notification(
            user=user,
            event_type=args[1],
            title=args[2],
            body=args[3],
            payload=args[4],
        )
        return str(notification.id)


async def _enqueue_pipeline(user: User, config: JobSearchConfig) -> str:
    try:
        return run_pipeline_for_config.delay(str(config.id), str(user.id)).id
    except Exception:
        log.warning(
            "job_config.enqueue_pipeline_failed",
            user_id=str(user.id),
            exc_info=True,
        )
        return await _enqueue_notification(user, config)


def _clean_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _require_staff(user: User) -> None:
    if not user.is_staff:
        raise ForbiddenError("Admin privileges are required.", code="admin_required")


def provider_to_response(
    provider: JobSourceProvider,
) -> JobSourceProviderResponse:
    return JobSourceProviderResponse(
        id=provider.id,
        slug=provider.slug,
        display_name=provider.display_name,
        docs_url=provider.docs_url,
        status=provider.status,
        robots_notes=provider.robots_notes,
        terms_notes=provider.terms_notes,
        last_discovered_at=provider.last_discovered_at,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def draft_to_response(
    draft: JobSourceConfigDraft,
) -> JobSourceConfigDraftResponse:
    return JobSourceConfigDraftResponse(
        id=draft.id,
        provider_id=draft.provider.id,
        config=draft.config,
        status=draft.status,
        confidence_score=draft.confidence_score,
        evidence_urls=draft.evidence_urls or [],
        validation_errors=draft.validation_errors or [],
        approved_at=draft.approved_at,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def validation_run_to_response(run: object) -> JobSourceValidationRunResponse:
    return JobSourceValidationRunResponse.model_validate(run)


__all__ = [
    "approve_config_draft",
    "create_config",
    "create_provider",
    "disable_config",
    "draft_to_response",
    "list_configs",
    "list_provider_drafts",
    "list_providers",
    "provider_to_response",
    "run_config",
    "schedule_presets",
    "to_response",
    "trigger_discovery",
    "update_config",
    "validate_draft",
]
