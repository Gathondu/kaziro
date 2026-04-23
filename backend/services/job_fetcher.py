"""RapidAPI job-search client (T2.2).

For a given :class:`JobSearchConfig` row this service:

1. Builds a query from the config's keywords, location, and remote
   flag.
2. Calls the configured RapidAPI provider (default: ``jsearch``) with
   exponential-backoff retries on 429 / 5xx responses.
3. Dedupes incoming jobs against existing ``raw_jobs`` rows on
   ``(source_api, external_id)`` and inserts the new ones with
   ``parse_status=PENDING``.
4. Records every call in the
   ``kaziro_external_api_calls_total{service="rapidapi"}`` Prometheus
   counter.

The Pipeline Orchestrator (T2.8) and the Celery beat task (T2.9) are
the only callers of :func:`fetch_jobs_for_config`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import get_settings
from backend.db.models.enums import JobSource
from backend.db.repositories import job_config_repository, raw_job_repository
from backend.db.session import async_session_factory
from backend.logging_config import get_logger
from backend.metrics import external_api_calls_total

log = get_logger(__name__)

DEFAULT_PAGE_LIMIT: Final[int] = 50
RETRYABLE_STATUS: Final[set[int]] = {429, 500, 502, 503, 504}


class JobFetchError(RuntimeError):
    """Raised when an upstream call fails after exhausting retries."""


class _RetryableUpstream(Exception):
    """Internal marker — caught by tenacity, re-raised as JobFetchError."""


def _build_query(*, keywords: list[str], location: str | None) -> str:
    """Concatenate keywords + location into the upstream's search string."""
    parts = list(keywords)
    if location:
        parts.append(location)
    return " ".join(p.strip() for p in parts if p and p.strip()).strip()


def _normalise_external_id(payload: dict[str, Any]) -> str | None:
    """Extract the upstream's stable identifier from a job payload."""
    for key in ("job_id", "id", "jobId", "external_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


async def _request_page(
    client: httpx.AsyncClient,
    *,
    query: str,
    page: int,
    remote_only: bool,
) -> list[dict[str, Any]]:
    """Issue a single HTTP request to RapidAPI and return the ``data`` list.

    Wraps retryable HTTP outcomes in :class:`_RetryableUpstream` so the
    outer ``AsyncRetrying`` wrapper can drive exponential backoff.
    """
    settings = get_settings()
    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY.get_secret_value(),
        "X-RapidAPI-Host": settings.RAPIDAPI_HOST,
        "Accept": "application/json",
    }
    params: dict[str, Any] = {
        "query": query,
        "page": str(page),
        "num_pages": "1",
    }
    if remote_only:
        params["remote_jobs_only"] = "true"

    url = f"https://{settings.RAPIDAPI_HOST}/search"
    try:
        resp = await client.get(url, headers=headers, params=params, timeout=30.0)
    except httpx.RequestError as exc:
        external_api_calls_total.labels(service="rapidapi", status="network_error").inc()
        raise _RetryableUpstream(f"network error: {exc}") from exc

    if resp.status_code in RETRYABLE_STATUS:
        external_api_calls_total.labels(service="rapidapi", status=str(resp.status_code)).inc()
        raise _RetryableUpstream(
            f"upstream returned retryable status {resp.status_code}"
        )

    if resp.status_code >= 400:
        external_api_calls_total.labels(service="rapidapi", status=str(resp.status_code)).inc()
        raise JobFetchError(
            f"rapidapi returned {resp.status_code}: {resp.text[:200]}"
        )

    external_api_calls_total.labels(service="rapidapi", status="200").inc()
    body = resp.json()
    data = body.get("data", []) if isinstance(body, dict) else []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    *,
    query: str,
    page: int,
    remote_only: bool,
    max_attempts: int = 3,
) -> list[dict[str, Any]]:
    async for attempt in AsyncRetrying(
        retry=retry_if_exception_type(_RetryableUpstream),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    ):
        with attempt:
            return await _request_page(
                client, query=query, page=page, remote_only=remote_only
            )
    return []


async def fetch_jobs_for_config(
    config_id: str | uuid.UUID, *, page_limit: int = DEFAULT_PAGE_LIMIT
) -> list[dict[str, Any]]:
    """Fetch + dedupe jobs for a saved search config.

    Returns the list of newly-inserted ``raw_jobs`` payloads (the same
    dicts that get persisted into ``raw_jobs.raw_payload`` and forwarded
    to the Parser Agent). Already-known ``(source_api, external_id)``
    rows are skipped without raising.
    """
    config_uuid = uuid.UUID(str(config_id))
    log_ctx = log.bind(config_id=str(config_uuid))

    async with async_session_factory() as session:
        config = await job_config_repository.get_by_id_unscoped(session, config_uuid)
        if config is None or not config.is_active:
            log_ctx.warning("job_fetcher.config_unavailable", active=getattr(config, "is_active", None))
            return []

        query = _build_query(keywords=config.keywords, location=config.location)
        if not query:
            log_ctx.warning("job_fetcher.empty_query")
            return []

        async with httpx.AsyncClient() as client:
            try:
                payloads = await _fetch_with_retry(
                    client,
                    query=query,
                    page=1,
                    remote_only=config.remote_only,
                )
            except _RetryableUpstream as exc:
                raise JobFetchError(str(exc)) from exc

        log_ctx.info("job_fetcher.upstream_returned", count=len(payloads))

        inserted: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for payload in payloads[:page_limit]:
            external_id = _normalise_external_id(payload)
            if not external_id:
                continue
            row = await raw_job_repository.insert_dedup(
                session,
                user_id=config.user_id,
                config_id=config.id,
                source_api=JobSource.RAPIDAPI,
                external_id=external_id,
                raw_payload=payload,
                fetched_at=now,
            )
            if row is not None:
                inserted.append(payload)
        await session.commit()

    log_ctx.info("job_fetcher.inserted", new=len(inserted))
    return inserted


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "JobFetchError",
    "fetch_jobs_for_config",
]
