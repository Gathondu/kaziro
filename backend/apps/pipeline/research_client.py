from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from apps.core.exceptions import UpstreamError
from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)


class ResearchSource(BaseModel):
    url: str
    canonical_url: str | None = None
    page_type: str
    title: str
    description: str = ""
    text: str
    structured_data: list[object] = Field(default_factory=list)
    retrieved_at: str
    warnings: list[str] = Field(default_factory=list)


class CompanyResearchEvidence(BaseModel):
    company_name: str
    selected_website: str | None = None
    selection_confidence: float = 0
    selection_evidence: list[dict[str, object]] = Field(default_factory=list)
    sources: list[ResearchSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    retrieved_at: str


class ExtractedPageEvidence(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    text: str = ""
    canonical_url: str | None = None
    structured_data: list[object] = Field(default_factory=list)


async def fetch_company_research(
    *,
    company_name: str,
    company_website: str | None,
    job_url: str,
) -> CompanyResearchEvidence:
    settings = get_settings()
    base_url = settings.SCRAPPER_COMPANY_RESEARCH_URL or settings.JOB_SOURCE_DISCOVERY_URL
    payload: dict[str, object] = {
        "company_name": company_name,
        "job_url": job_url,
        "max_depth": 1,
        "max_pages": 8,
    }
    if company_website:
        payload["company_website"] = company_website
    response = await asyncio.to_thread(
        _post_json,
        f"{base_url.rstrip('/')}/research/company",
        payload,
        settings.SCRAPPER_COMPANY_RESEARCH_TIMEOUT_SECONDS,
    )
    try:
        return CompanyResearchEvidence.model_validate(response)
    except ValueError as exc:
        raise UpstreamError(
            "Scrapper returned invalid company research.",
            code="company_research_invalid_payload",
        ) from exc


async def extract_page(url: str) -> ExtractedPageEvidence:
    settings = get_settings()
    base_url = settings.SCRAPPER_COMPANY_RESEARCH_URL or settings.JOB_SOURCE_DISCOVERY_URL
    response = await asyncio.to_thread(
        _post_json,
        f"{base_url.rstrip('/')}/extract-page",
        {"url": url, "max_depth": 0, "max_pages": 1},
        settings.SCRAPPER_COMPANY_RESEARCH_TIMEOUT_SECONDS,
    )
    pages = response.get("pages")
    if not isinstance(pages, list) or not pages:
        raise UpstreamError(
            "Scrapper returned no page content.",
            code="job_url_no_content",
        )
    try:
        return ExtractedPageEvidence.model_validate(pages[0])
    except ValueError as exc:
        raise UpstreamError(
            "Scrapper returned invalid page content.",
            code="job_url_invalid_payload",
        ) from exc


def _post_json(url: str, payload: dict[str, object], timeout: int) -> dict[str, Any]:
    settings = get_settings()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.SCRAPPER_API_KEY is not None:
        headers["X-Scrapper-Key"] = settings.SCRAPPER_API_KEY.get_secret_value()
    request = Request(
        url,
        method="POST",
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode())
    except HTTPError as exc:
        upstream_message = _http_error_message(exc)
        log.error(
            "company_research.http_error",
            status_code=exc.code,
            error=upstream_message,
        )
        raise UpstreamError(
            "Company research service is unavailable.",
            code="company_research_unavailable",
        ) from exc
    except (URLError, OSError, json.JSONDecodeError) as exc:
        log.error(
            "company_research.request_failed",
            error=exc.__class__.__name__,
            message=str(exc)[:512],
        )
        raise UpstreamError(
            "Company research service is unavailable.",
            code="company_research_unavailable",
        ) from exc
    if not isinstance(value, dict):
        raise UpstreamError(
            "Scrapper returned invalid company research.",
            code="company_research_invalid_payload",
        )
    return value


def _http_error_message(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode())
    except OSError, UnicodeDecodeError, json.JSONDecodeError:
        return exc.reason[:512] if isinstance(exc.reason, str) else "HTTP request failed"
    if not isinstance(payload, dict):
        return "HTTP request failed"
    message = payload.get("message") or payload.get("error") or "HTTP request failed"
    return str(message)[:512]


__all__ = [
    "CompanyResearchEvidence",
    "ExtractedPageEvidence",
    "ResearchSource",
    "extract_page",
    "fetch_company_research",
]
