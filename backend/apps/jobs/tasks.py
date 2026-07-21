from __future__ import annotations

import re

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.jobs import discovery_client, fetcher, repositories
from apps.jobs.models import (
    DiscoveryRunStatus,
    DraftStatus,
    JobSourceConfigDraft,
    JobSourceDiscoveryRun,
    JobSourceProvider,
    JobSourceValidationRun,
    ProviderStatus,
)
from config.celery import QUEUE_DISCOVERY, app, run_async
from config.logging import get_logger

log = get_logger(__name__)


@app.task(name="apps.jobs.discover_provider", queue=QUEUE_DISCOVERY)
def discover_provider_task(
    provider_id: str,
    discovery_run_id: str | None = None,
    known_auth_type: str | None = None,
    keywords: list[str] | None = None,
) -> str:
    return run_async(
        lambda: _discover_provider(provider_id, discovery_run_id, known_auth_type, keywords)
    )


@app.task(name="apps.jobs.validate_provider_draft", queue=QUEUE_DISCOVERY)
def validate_provider_draft_task(draft_id: str) -> str:
    return run_async(lambda: _validate_provider_draft(draft_id))


async def _discover_provider(
    provider_id: str,
    discovery_run_id: str | None,
    known_auth_type: str | None,
    keywords: list[str] | None,
) -> str:
    provider = await repositories.get_provider(provider_id)
    if provider is None:
        raise ValueError("Provider not found.")
    run = await _get_or_create_discovery_run(provider, discovery_run_id, known_auth_type, keywords)
    run.status = DiscoveryRunStatus.RUNNING
    run.started_at = timezone.now()
    await run.asave(update_fields=["status", "started_at"])
    log.info(
        "job_source.discovery_start",
        provider_id=str(provider.id),
        discovery_run_id=str(run.id),
        slug=provider.slug,
    )
    try:
        result = await discovery_client.discover_provider_config(
            provider_slug=provider.slug,
            docs_url=provider.docs_url,
            known_auth_type=known_auth_type,
            keywords=keywords,
        )
        draft = await repositories.create_draft(
            provider,
            config=result.config,
            confidence_score=result.confidence_score,
            evidence_urls=result.evidence_urls,
        )
    except Exception as exc:
        run.status = DiscoveryRunStatus.FAILED
        run.error_message = _safe_error_message(exc)
        run.completed_at = timezone.now()
        await run.asave(update_fields=["status", "error_message", "completed_at"])
        log.error(
            "job_source.discovery_failed",
            provider_id=str(provider.id),
            discovery_run_id=str(run.id),
            error=type(exc).__name__,
        )
        raise

    run.status = DiscoveryRunStatus.SUCCEEDED
    run.draft = draft
    run.metadata = result.metadata
    run.error_message = ""
    run.completed_at = timezone.now()
    await run.asave(update_fields=["status", "draft", "metadata", "error_message", "completed_at"])
    provider.last_discovered_at = timezone.now()
    await provider.asave(update_fields=["last_discovered_at", "updated_at"])
    log.info(
        "job_source.discovery_draft_created",
        provider_id=str(provider.id),
        discovery_run_id=str(run.id),
        draft_id=str(draft.id),
    )
    return str(draft.id)


async def _get_or_create_discovery_run(
    provider: JobSourceProvider,
    discovery_run_id: str | None,
    known_auth_type: str | None,
    keywords: list[str] | None,
) -> JobSourceDiscoveryRun:
    if discovery_run_id:
        run = await JobSourceDiscoveryRun.objects.filter(
            id=discovery_run_id, provider=provider
        ).afirst()
        if run is None:
            raise ValueError("Discovery run not found.")
        return run
    return await repositories.create_discovery_run(
        provider, known_auth_type=known_auth_type, keywords=keywords
    )


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or "Discovery failed."
    message = re.sub(
        r"(?i)(api[_-]?key|token|authorization)\s*[:=]\s*\S+", r"\1=<redacted>", message
    )
    message = re.sub(r"([?&][^=\s]+)=([^&\s]+)", r"\1=<redacted>", message)
    return message[:1000]


async def _validate_provider_draft(draft_id: str) -> str:
    draft = await repositories.get_draft(draft_id)
    if draft is None:
        raise ValueError("Draft not found.")
    (
        ok,
        request_url,
        request_headers,
        response_status,
        metadata,
        response_payload,
        errors,
    ) = await fetcher.validate_draft_with_smoke_request(draft)
    draft.status = DraftStatus.VALIDATED if ok else DraftStatus.VALIDATION_FAILED
    draft.validation_errors = errors
    await draft.asave(update_fields=["status", "validation_errors", "updated_at"])
    run = await JobSourceValidationRun.objects.acreate(
        draft=draft,
        status=draft.status,
        request_url=request_url,
        request_headers=request_headers,
        response_status=response_status,
        response_metadata=metadata,
        response_payload=response_payload,
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
    provider_slug = await sync_to_async(_approve_draft_sync, thread_sensitive=True)(draft_id)
    log.info("job_source.draft_approved", draft_id=draft_id, provider=provider_slug)
    return draft_id


@transaction.atomic
def _approve_draft_sync(draft_id: str) -> str:
    draft = (
        JobSourceConfigDraft.objects.select_for_update()
        .select_related("provider")
        .filter(id=draft_id)
        .first()
    )
    if draft is None:
        raise ValueError("Draft not found.")
    if draft.status != DraftStatus.VALIDATED:
        raise ValueError("Only validated drafts can be approved.")
    provider = JobSourceProvider.objects.select_for_update().get(id=draft.provider_id)
    now = timezone.now()
    JobSourceConfigDraft.objects.filter(provider=provider, status=DraftStatus.APPROVED).exclude(
        id=draft.id
    ).update(status=DraftStatus.SUPERSEDED, updated_at=now)
    draft.status = DraftStatus.APPROVED
    draft.approved_at = now
    draft.save(update_fields=["status", "approved_at", "updated_at"])
    provider.status = ProviderStatus.ACTIVE
    provider.save(update_fields=["status", "updated_at"])
    return provider.slug


__all__ = [
    "approve_draft",
    "discover_provider_task",
    "validate_provider_draft_task",
]
