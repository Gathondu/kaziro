"""Import a single user-submitted job URL into the existing pipeline."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any, Final, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx

from backend.agents.parser_agent import run_parser_agent
from backend.agents.pipeline_orchestrator import run_pipeline_for_single_job
from backend.config import get_settings
from backend.db.models.enums import JobSource
from backend.db.repositories import job_posting_repository, raw_job_repository
from backend.db.session import async_session_factory
from backend.logging_config import get_logger
from backend.metrics import external_api_calls_total
from backend.services.notifications import get_redis, notify_user

log = get_logger(__name__)

DEFAULT_FIRECRAWL_BASE: Final[str] = "https://api.firecrawl.dev/v1"
SCRAPE_MAX_CHARS: Final[int] = 60_000
IMPORT_LOCK_TTL_SEC: Final[int] = 900
IMPORT_LOCK_WAIT_SEC: Final[float] = 30.0


class JobUrlImportInProgress(RuntimeError):
    """Raised when another worker is parsing this URL and Celery should retry."""


class JobUrlImportError(RuntimeError):
    """Raised for user-facing import failures."""


class JobUrlScraper(Protocol):
    async def scrape(self, url: str, *, max_chars: int = SCRAPE_MAX_CHARS) -> str: ...


class _FirecrawlJobUrlScraper:
    """Small Firecrawl client for exact job-page extraction."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self._base = (
            str(settings.FIRECRAWL_BASE_URL)
            if settings.FIRECRAWL_BASE_URL
            else (base_url or DEFAULT_FIRECRAWL_BASE)
        ).rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }

    async def scrape(self, url: str, *, max_chars: int = SCRAPE_MAX_CHARS) -> str:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self._base}/scrape",
                    headers=self._headers,
                    json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                )
        except httpx.RequestError as exc:
            external_api_calls_total.labels(service="firecrawl", status="network_error").inc()
            raise JobUrlImportError("Could not fetch the job page.") from exc

        external_api_calls_total.labels(service="firecrawl", status=str(response.status_code)).inc()
        if response.status_code >= 400:
            raise JobUrlImportError("Could not fetch the job page.")
        try:
            data = response.json()
        except ValueError as exc:
            raise JobUrlImportError("The job page scraper returned an invalid response.") from exc
        payload = data.get("data") if isinstance(data, dict) else None
        markdown = ""
        if isinstance(payload, dict):
            markdown = str(payload.get("markdown", "") or "")
        elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
            markdown = str(payload[0].get("markdown", "") or "")
        return markdown[:max_chars]


_scraper: JobUrlScraper | None = None


def get_job_url_scraper() -> JobUrlScraper:
    global _scraper
    if _scraper is None:
        _scraper = _FirecrawlJobUrlScraper()
    return _scraper


def set_job_url_scraper_for_tests(scraper: JobUrlScraper | None) -> None:
    global _scraper
    _scraper = scraper


def normalize_job_url(raw_url: str) -> str:
    """Normalize a user-submitted URL for dedupe while preserving ATS query IDs."""
    candidate = raw_url.strip()
    if not candidate:
        raise ValueError("URL is required.")
    parsed = urlsplit(candidate)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a valid http or https URL.")
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def manual_url_hash(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


def manual_url_external_id(normalized_url: str) -> str:
    return f"{JobSource.MANUAL_URL.value}:{manual_url_hash(normalized_url)}"


def user_import_lock_key(user_id: str | uuid.UUID, normalized_url: str) -> str:
    return f"job_import:user:{user_id}:{manual_url_hash(normalized_url)}"


async def clear_user_import_lock(raw_url: str, user_id: str) -> None:
    normalized = normalize_job_url(raw_url)
    await get_redis().delete(user_import_lock_key(user_id, normalized))


async def import_job_url_for_user(
    raw_url: str, user_id: str, company_url: str | None = None
) -> dict[str, Any]:
    """Scrape, parse, and run the single-job pipeline for a pasted job URL."""
    normalized = normalize_job_url(raw_url)
    company_normalized_url = normalize_job_url(company_url) if company_url else None
    external_id = manual_url_external_id(normalized)
    url_hash = manual_url_hash(normalized)
    bound = log.bind(user_id=user_id, url_hash=url_hash)

    posting_id = await _posting_id_for_external_id(external_id)
    if posting_id is None:
        posting_id = await _create_posting_from_url(
            normalized, external_id, user_id, bound, company_normalized_url
        )

    result = await run_pipeline_for_single_job(posting_id, user_id)
    return {"url": normalized, "job_posting_id": posting_id, **result}


async def import_job_url_for_user_with_failure_notification(
    raw_url: str,
    user_id: str,
    company_url: str | None = None,
) -> dict[str, Any]:
    """Import wrapper used by Celery so user-visible failures become toasts."""
    normalized = raw_url.strip()
    normalized_company_url = company_url.strip() if company_url else None
    try:
        normalized = normalize_job_url(raw_url)
        return await import_job_url_for_user(normalized, user_id, normalized_company_url)
    except JobUrlImportInProgress:
        raise
    except Exception as exc:
        reason = _safe_failure_reason(exc)
        await notify_user(
            user_id, {"type": "job_import_failed", "url": normalized, "reason": reason}
        )
        log.warning("job_url_import.failed", user_id=user_id, url=normalized, reason=reason)
        return {"url": normalized, "error": reason}


async def process_job_url_import_now(
    raw_url: str, user_id: str, company_url: str | None = None
) -> dict[str, Any]:
    """Run the URL import immediately from an API background task."""
    normalized = raw_url.strip()
    normalized_company_url = company_url.strip() if company_url else None
    try:
        normalized = normalize_job_url(raw_url)
        return await import_job_url_for_user_with_failure_notification(
            normalized, user_id, normalized_company_url
        )
    except JobUrlImportInProgress:
        reason = "That job URL is already being imported. Please try again shortly."
        await notify_user(
            user_id, {"type": "job_import_failed", "url": normalized, "reason": reason}
        )
        return {"url": normalized, "error": reason}
    finally:
        try:
            await clear_user_import_lock(normalized, user_id)
        except Exception:
            log.warning("job_url_import.user_lock_cleanup_failed", user_id=user_id)


async def _posting_id_for_external_id(external_id: str) -> str | None:
    async with async_session_factory() as session:
        posting = await job_posting_repository.get_by_external_id(session, external_id)
    return str(posting.id) if posting is not None else None


async def _create_posting_from_url(
    normalized_url: str,
    external_id: str,
    user_id: str,
    bound: Any,
    company_url: str | None,
) -> str:
    key = f"job_import:url:{manual_url_hash(normalized_url)}"
    redis = get_redis()
    got_lock = await redis.set(key, "PENDING", nx=True, ex=IMPORT_LOCK_TTL_SEC)
    if not got_lock:
        posting_id = await _wait_for_existing_posting(external_id)
        if posting_id is not None:
            return posting_id
        raise JobUrlImportInProgress("Job URL import is already in progress.")

    try:
        markdown = await get_job_url_scraper().scrape(normalized_url)
        if not markdown.strip():
            raise JobUrlImportError("The job page did not contain readable job text.")
        raw_job_id = await _insert_or_get_raw_job(
            user_id=uuid.UUID(user_id),
            external_id=external_id,
            normalized_url=normalized_url,
            company_url=company_url,
            scraped_markdown=markdown,
        )
        parsed = await run_parser_agent(raw_job_id, await _raw_payload(raw_job_id))
        if parsed.error or not parsed.job_posting_id:
            raise JobUrlImportError("Kaziro could not parse that job page.")
        bound.info(
            "job_url_import.parsed", raw_job_id=raw_job_id, job_posting_id=parsed.job_posting_id
        )
        return parsed.job_posting_id
    finally:
        await redis.delete(key)


async def _wait_for_existing_posting(external_id: str) -> str | None:
    deadline = asyncio.get_running_loop().time() + IMPORT_LOCK_WAIT_SEC
    while asyncio.get_running_loop().time() < deadline:
        posting_id = await _posting_id_for_external_id(external_id)
        if posting_id is not None:
            return posting_id
        await asyncio.sleep(1.0)
    return None


async def _insert_or_get_raw_job(
    *,
    user_id: uuid.UUID,
    external_id: str,
    normalized_url: str,
    company_url: str | None = None,
    scraped_markdown: str,
) -> str:
    fetched_at = datetime.now(UTC)
    payload: dict[str, Any] = {
        "job_id": external_id,
        "external_id": external_id,
        "source_url": normalized_url,
        "application_url": normalized_url,
        "company_url": company_url or normalized_url,
        "scraped_markdown": scraped_markdown,
        "fetched_at": fetched_at.isoformat(),
    }
    async with async_session_factory() as session:
        row = await raw_job_repository.insert_dedup(
            session,
            user_id=user_id,
            config_id=None,
            source_api=JobSource.MANUAL_URL,
            external_id=external_id,
            raw_payload=payload,
            fetched_at=fetched_at,
        )
        if row is None:
            row = await raw_job_repository.get_by_source_external(
                session,
                source_api=JobSource.MANUAL_URL,
                external_id=external_id,
            )
        if row is None:
            raise JobUrlImportError("Could not save the job page for parsing.")
        raw_id = str(row.id)
        await session.commit()
    return raw_id


async def _raw_payload(raw_job_id: str) -> dict[str, Any]:
    from backend.db.models.raw_job import RawJob

    async with async_session_factory() as session:
        raw = await session.get(RawJob, uuid.UUID(raw_job_id))
    if raw is None:
        raise JobUrlImportError("Could not load the saved job page.")
    return dict(raw.raw_payload)


def _safe_failure_reason(exc: Exception) -> str:
    if isinstance(exc, ValueError | JobUrlImportError):
        return str(exc)
    return "Kaziro could not import that job URL."


__all__ = [
    "JobUrlImportError",
    "JobUrlImportInProgress",
    "JobUrlScraper",
    "clear_user_import_lock",
    "import_job_url_for_user",
    "import_job_url_for_user_with_failure_notification",
    "manual_url_external_id",
    "manual_url_hash",
    "normalize_job_url",
    "process_job_url_import_now",
    "set_job_url_scraper_for_tests",
    "user_import_lock_key",
]
