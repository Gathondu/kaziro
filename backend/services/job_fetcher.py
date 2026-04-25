"""RapidAPI job-search client (JSearch) with Supabase cache.

For a given :class:`JobSearchConfig` row this service:

1. Normalizes keywords into sorted slug segments and derives a storage object
   basename (``slug++slug.json`` in the job-posts bucket).
2. Lists the Supabase job-posts bucket and **reuses** a prior JSON payload when
   keyword slugs **overlap** or the cached search is a **superset** of the
   current keywords (see :func:`job_posts_cache.pick_best_cache_object_name`).
3. On cache miss, calls OpenRouter (:mod:`rapidapi_query_builder`) with the
   embedded API reference to obtain a validated path + query params, performs
   a single RapidAPI GET (retries on 429/5xx with ``Retry-After`` support;
   see ``RAPIDAPI_FETCH_MAX_ATTEMPTS``), stores the JSON envelope
   in Storage, and parses job dicts from the upstream body.
4. Dedupes incoming jobs against existing ``raw_jobs`` rows on
   ``(source_api, external_id)`` and inserts new ones with ``parse_status=PENDING``.
5. Records RapidAPI calls in ``kaziro_external_api_calls_total``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final, cast

import httpx
from langsmith import traceable
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
)
from tenacity.wait import wait_base

from backend.config import Settings, get_settings
from backend.db.models.enums import JobSource
from backend.db.repositories import job_config_repository, raw_job_repository
from backend.db.session import async_session_factory
from backend.logging_config import get_logger
from backend.metrics import external_api_calls_total
from backend.services import job_posts_cache, rapidapi_query_builder
from backend.services.rapidapi_retry_utils import parse_retry_after_seconds

log = get_logger(__name__)

DEFAULT_PAGE_LIMIT: Final[int] = 100
RETRYABLE_STATUS: Final[set[int]] = {429, 500, 502, 503, 504}


class JobFetchError(RuntimeError):
    """Raised when an upstream call fails after exhausting retries."""


class _RetryableUpstream(Exception):
    """Internal marker — caught by tenacity, re-raised as JobFetchError."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
        is_rate_limited: bool = False,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.is_rate_limited = is_rate_limited


class _RapidApiRetryWait(wait_base):
    """Honor ``Retry-After`` on 429; otherwise back off longer for rate limits than for 5xx."""

    def __init__(
        self,
        *,
        cap_s: float,
        min_s: float = 2.0,
        max_s: float = 90.0,
        default_429_s: float = 20.0,
    ) -> None:
        self.cap_s = cap_s
        self.min_s = min_s
        self.max_s = max_s
        self.default_429_s = default_429_s

    def __call__(self, retry_state: RetryCallState) -> float:
        outcome = retry_state.outcome
        if outcome is None:
            return self.min_s
        exc_obj = outcome.exception()
        if not isinstance(exc_obj, _RetryableUpstream):
            return self.min_s
        exc = exc_obj
        if exc.retry_after_seconds is not None:
            wait = min(max(exc.retry_after_seconds, self.min_s), self.cap_s)
            return float(wait)
        if exc.is_rate_limited:
            n = max(1, retry_state.attempt_number)
            wait = min(self.max_s, max(self.min_s, self.default_429_s * float(n)))
            return float(wait)
        n = max(1, retry_state.attempt_number)
        wait = min(self.max_s, max(self.min_s, 2.0 ** float(n - 1)))
        return float(wait)


def extract_job_list_from_upstream(body: Any) -> list[dict[str, Any]]:
    """Return job dicts from a RapidAPI JSON body (shape-tolerant)."""
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        for key in ("data", "items", "jobs", "results"):
            chunk = body.get(key)
            if isinstance(chunk, list):
                return [item for item in chunk if isinstance(item, dict)]
    return []


def _normalise_external_id(payload: dict[str, Any]) -> str | None:
    """Extract the upstream's stable identifier from a job payload."""
    for key in ("job_id", "id", "jobId", "external_id", "url", "job_url", "link"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _trace_request_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    query_pairs = inputs.get("query_pairs", [])
    return {
        "url": inputs.get("url"),
        "query_pairs_count": len(query_pairs) if isinstance(query_pairs, list) else 0,
    }


def _trace_request_outputs(output: Any) -> dict[str, Any]:
    if isinstance(output, dict):
        return {"output_keys": sorted(output.keys())}
    if isinstance(output, list):
        return {"output_len": len(output)}
    return {"output_type": type(output).__name__}


@traceable(
    run_type="tool",
    name="rapidapi.request",
    tags=["rapidapi", "fetch"],
    process_inputs=_trace_request_inputs,
    process_outputs=_trace_request_outputs,
)
async def _request_rapidapi(
    client: httpx.AsyncClient,
    *,
    url: str,
    query_pairs: list[tuple[str, str]],
) -> Any:
    settings = get_settings()
    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY.get_secret_value(),
        "X-RapidAPI-Host": settings.RAPIDAPI_HOST,
        "Accept": "application/json",
    }
    try:
        resp = await client.get(
            url,
            headers=headers,
            params=httpx.QueryParams(cast(Any, query_pairs)),
            timeout=60.0,
        )
    except httpx.RequestError as exc:
        external_api_calls_total.labels(service="rapidapi", status="network_error").inc()
        raise _RetryableUpstream(f"network error: {exc}") from exc

    if resp.status_code in RETRYABLE_STATUS:
        external_api_calls_total.labels(service="rapidapi", status=str(resp.status_code)).inc()
        ra: float | None = None
        is_rl = resp.status_code == 429
        if is_rl:
            ra = parse_retry_after_seconds(resp.headers, status_code=429)
        log.warning(
            "job_fetcher.rapidapi_retryable_response",
            error=f"http_{resp.status_code}",
            status_code=resp.status_code,
            retry_after_s=ra,
        )
        raise _RetryableUpstream(
            f"upstream returned retryable status {resp.status_code}",
            retry_after_seconds=ra,
            is_rate_limited=is_rl,
        )

    if resp.status_code >= 400:
        external_api_calls_total.labels(service="rapidapi", status=str(resp.status_code)).inc()
        raise JobFetchError(f"rapidapi returned {resp.status_code}: {resp.text[:200]}")

    external_api_calls_total.labels(service="rapidapi", status="200").inc()
    return resp.json()


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    *,
    url: str,
    query_pairs: list[tuple[str, str]],
    settings: Settings | None = None,
) -> Any:
    s = settings or get_settings()
    wait = _RapidApiRetryWait(cap_s=float(s.RAPIDAPI_FETCH_RETRY_AFTER_CAP_S))
    async for attempt in AsyncRetrying(
        retry=retry_if_exception_type(_RetryableUpstream),
        stop=stop_after_attempt(s.RAPIDAPI_FETCH_MAX_ATTEMPTS),
        wait=wait,
        reraise=True,
    ):
        with attempt:
            return await _request_rapidapi(client, url=url, query_pairs=query_pairs)
    raise RuntimeError("job_fetcher._fetch_with_retry: unreachable")


def _trace_fetch_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "config_id": str(inputs.get("config_id")),
        "has_page_limit": inputs.get("page_limit") is not None,
    }


def _trace_fetch_outputs(output: Any) -> dict[str, Any]:
    if isinstance(output, list):
        return {"inserted_count": len(output)}
    return {"output_type": type(output).__name__}


@traceable(
    run_type="chain",
    name="rapidapi.fetch_jobs_for_config",
    tags=["rapidapi", "job_fetcher"],
    process_inputs=_trace_fetch_inputs,
    process_outputs=_trace_fetch_outputs,
)
async def fetch_jobs_for_config(
    config_id: str | uuid.UUID,
    *,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch + dedupe jobs for a saved search config (cache-aware, one RapidAPI GET per miss)."""
    settings = get_settings()
    eff_limit = (
        page_limit
        if page_limit is not None
        else min(
            DEFAULT_PAGE_LIMIT,
            settings.RAPIDAPI_JOB_FETCH_LIMIT,
        )
    )
    config_uuid = uuid.UUID(str(config_id))
    log_ctx = log.bind(config_id=str(config_uuid))

    async with async_session_factory() as session:
        config = await job_config_repository.get_by_id_unscoped(session, config_uuid)
        if config is None or not config.is_active:
            log_ctx.warning(
                "job_fetcher.config_unavailable",
                active=getattr(config, "is_active", None),
            )
            return []

        log_ctx = log_ctx.bind(user_id=str(config.user_id))
        slugs = job_posts_cache.keyword_slugs(list(config.keywords))
        if not slugs:
            log_ctx.warning("job_fetcher.empty_keywords")
            return []

        basename = job_posts_cache.cache_object_basename(list(config.keywords))
        slug_set = set(slugs)
        listing: list[dict[str, Any]] = []
        try:
            listing = await job_posts_cache.list_cache_objects()
        except Exception:
            log_ctx.warning("job_fetcher.cache_list_failed")

        cache_name = job_posts_cache.pick_best_cache_object_name(
            current_slugs=slug_set,
            exact_basename=basename,
            listing=listing,
        )

        upstream_body: Any | None = None
        if cache_name:
            raw_envelope = await job_posts_cache.try_load_cache_json(cache_name)
            if raw_envelope is not None:
                upstream_body = job_posts_cache.parse_cache_payload(raw_envelope)
                log_ctx.info(
                    "job_fetcher.cache_hit",
                    cache_object=cache_name,
                    exact_match=cache_name == f"{basename}.json",
                )

        if upstream_body is None:
            log_ctx.info("job_fetcher.cache_miss")
            try:
                spec = await rapidapi_query_builder.build_query_spec_via_llm(
                    keywords=list(config.keywords),
                    location=config.location,
                    remote_only=config.remote_only,
                    employment_types=list(config.employment_types),
                    salary_min=config.salary_min,
                    salary_max=config.salary_max,
                    settings=settings,
                )
                url, pairs = rapidapi_query_builder.build_get_url_and_params(
                    spec, settings=settings
                )
            except (ValueError, TypeError) as exc:
                log_ctx.error("job_fetcher.query_spec_invalid", error=str(exc))
                raise JobFetchError(f"invalid rapidapi query spec: {exc}") from exc
            except Exception as exc:
                log_ctx.exception("job_fetcher.query_spec_failed", error=str(exc))
                raise JobFetchError("openrouter query build failed") from exc

            async with httpx.AsyncClient() as client:
                try:
                    body = await _fetch_with_retry(
                        client, url=url, query_pairs=pairs, settings=settings
                    )
                except _RetryableUpstream as exc:
                    raise JobFetchError(str(exc)) from exc

            if isinstance(body, dict):
                upstream_body = body
            elif isinstance(body, list):
                upstream_body = {"data": body}
            else:
                upstream_body = {}
            fetched_at = datetime.now(UTC).isoformat()
            try:
                await job_posts_cache.save_cache_envelope(
                    object_name=f"{basename}.json",
                    keyword_slugs=slugs,
                    upstream=upstream_body,
                    fetched_at_iso=fetched_at,
                )
            except Exception:
                log_ctx.exception("job_fetcher.cache_write_failed")

        assert upstream_body is not None
        payloads = extract_job_list_from_upstream(upstream_body)
        log_ctx.info("job_fetcher.upstream_returned", count=len(payloads))

        inserted: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for payload in payloads[:eff_limit]:
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
    "extract_job_list_from_upstream",
    "fetch_jobs_for_config",
]
