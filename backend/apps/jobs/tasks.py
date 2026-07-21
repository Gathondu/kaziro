from __future__ import annotations

from django.utils import timezone

from apps.jobs import discovery_client, fetcher, repositories
from apps.jobs.models import DraftStatus, JobSourceValidationRun, ProviderStatus
from apps.jobs.source_config import validate_provider_config
from config.celery import QUEUE_DISCOVERY, app, run_async
from config.logging import get_logger

log = get_logger(__name__)


@app.task(name="apps.jobs.discover_provider", queue=QUEUE_DISCOVERY)
def discover_provider_task(
    provider_id: str,
    known_auth_type: str | None = None,
    keywords: list[str] | None = None,
) -> str:
    return run_async(lambda: _discover_provider(provider_id, known_auth_type, keywords))


@app.task(name="apps.jobs.validate_provider_draft", queue=QUEUE_DISCOVERY)
def validate_provider_draft_task(draft_id: str) -> str:
    return run_async(lambda: _validate_provider_draft(draft_id))


async def _discover_provider(
    provider_id: str,
    known_auth_type: str | None,
    keywords: list[str] | None,
) -> str:
    provider = await repositories.get_provider(provider_id)
    if provider is None:
        raise ValueError("Provider not found.")
    log.info("job_source.discovery_start", provider_id=str(provider.id), slug=provider.slug)
    config = await discovery_client.discover_provider_config(
        provider_slug=provider.slug,
        docs_url=provider.docs_url,
        known_auth_type=known_auth_type,
        keywords=keywords,
    )
    validated_config = validate_provider_config(config)
    draft = await repositories.create_draft(
        provider,
        config=validated_config.model_dump(mode="json"),
        confidence_score=validated_config.confidence_score,
        evidence_urls=validated_config.evidence_urls,
    )
    provider.last_discovered_at = timezone.now()
    await provider.asave(update_fields=["last_discovered_at", "updated_at"])
    log.info(
        "job_source.discovery_draft_created",
        provider_id=str(provider.id),
        draft_id=str(draft.id),
    )
    return str(draft.id)


async def _validate_provider_draft(draft_id: str) -> str:
    draft = await repositories.get_draft(draft_id)
    if draft is None:
        raise ValueError("Draft not found.")
    (
        ok,
        request_url,
        response_status,
        metadata,
        errors,
    ) = await fetcher.validate_draft_with_smoke_request(draft)
    draft.status = DraftStatus.VALIDATED if ok else DraftStatus.VALIDATION_FAILED
    draft.validation_errors = errors
    await draft.asave(update_fields=["status", "validation_errors", "updated_at"])
    run = await JobSourceValidationRun.objects.acreate(
        draft=draft,
        status=draft.status,
        request_url=request_url,
        response_status=response_status,
        response_metadata=metadata,
        errors=errors,
    )
    log.info(
        "job_source.validation_completed",
        draft_id=str(draft.id),
        validation_run_id=str(run.id),
        status=draft.status,
    )
    return str(run.id)


async def approve_draft(draft_id: str) -> str:
    draft = await repositories.get_draft(draft_id)
    if draft is None:
        raise ValueError("Draft not found.")
    if draft.status != DraftStatus.VALIDATED:
        raise ValueError("Only validated drafts can be approved.")
    draft.status = DraftStatus.APPROVED
    draft.approved_at = timezone.now()
    draft.provider.status = ProviderStatus.ACTIVE
    await draft.asave(update_fields=["status", "approved_at", "updated_at"])
    await draft.provider.asave(update_fields=["status", "updated_at"])
    log.info("job_source.draft_approved", draft_id=str(draft.id), provider=draft.provider.slug)
    return str(draft.id)


__all__ = [
    "approve_draft",
    "discover_provider_task",
    "validate_provider_draft_task",
]
