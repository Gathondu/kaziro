from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from apps.core.exceptions import UpstreamError
from apps.jobs.source_config import validate_provider_config
from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    config: dict[str, object]
    confidence_score: float
    evidence_urls: list[str]
    metadata: dict[str, object]


async def discover_provider_config(
    *,
    provider_slug: str,
    docs_url: str,
    known_auth_type: str | None = None,
    keywords: list[str] | None = None,
) -> DiscoveryResult:
    settings = get_settings()
    payload: dict[str, object] = {
        "provider_slug": provider_slug,
        "docs_url": docs_url,
        "keywords": keywords or [],
    }
    if known_auth_type:
        payload["known_auth_type"] = known_auth_type
    response = await _post_json(
        f"{settings.JOB_SOURCE_DISCOVERY_URL.rstrip('/')}/discover",
        payload,
        timeout=settings.JOB_SOURCE_DISCOVERY_TIMEOUT_SECONDS,
    )
    return _normalize_discovery_response(response)


def _normalize_discovery_response(response: dict[str, Any]) -> DiscoveryResult:
    draft = response.get("draft")
    if not isinstance(draft, dict):
        raise UpstreamError(
            "Job source discovery returned an invalid payload.",
            code="job_source_discovery_invalid_payload",
        )
    normalized_draft = _normalize_rapidapi_draft(draft, response)
    try:
        config = validate_provider_config(normalized_draft).model_dump(mode="json")
    except ValueError as exc:
        log.warning(
            "job_source.discovery_invalid_draft",
            error=str(exc),
        )
        raise UpstreamError(
            "Job source discovery returned an invalid provider draft.",
            code="job_source_discovery_invalid_payload",
        ) from exc

    confidence = response.get("confidence_score", config.get("confidence_score", 0))
    evidence = response.get("evidence_urls", config.get("evidence_urls", []))
    if not isinstance(confidence, int | float) or not isinstance(evidence, list):
        raise UpstreamError(
            "Job source discovery returned invalid draft metadata.",
            code="job_source_discovery_invalid_payload",
        )
    metadata_keys = (
        "warnings",
        "endpoint_candidates",
        "auth_candidates",
        "pagination_candidates",
        "response_mapping_candidates",
    )
    metadata = {key: response[key] for key in metadata_keys if key in response}
    return DiscoveryResult(
        config=config,
        confidence_score=float(confidence),
        evidence_urls=[str(item) for item in evidence],
        metadata=metadata,
    )


def _normalize_rapidapi_draft(draft: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(draft)
    base_url = str(normalized.get("base_url") or "")
    if not _is_rapidapi_draft(normalized, base_url):
        return normalized

    auth = dict(normalized.get("auth") or {})
    if auth.get("type") != "none":
        auth["credential_env_var"] = "RAPIDAPI_KEY"
        normalized["auth"] = auth

    host = _discovered_rapidapi_host(draft, response, base_url)
    if not host:
        return normalized
    headers = [dict(header) for header in normalized.get("request_headers", [])]
    host_header = next(
        (header for header in headers if str(header.get("name", "")).lower() == "x-rapidapi-host"),
        None,
    )
    if host_header is None:
        headers.append({"name": "X-RapidAPI-Host", "value": host})
    else:
        host_header.pop("value_env_var", None)
        host_header["value"] = host
    normalized["request_headers"] = headers
    return normalized


def _is_rapidapi_draft(draft: dict[str, Any], base_url: str) -> bool:
    if "rapidapi.com" in urlsplit(base_url).netloc.lower():
        return True
    auth = draft.get("auth")
    if isinstance(auth, dict) and str(auth.get("header_name", "")).lower() == "x-rapidapi-key":
        return True
    return any(
        isinstance(header, dict) and str(header.get("name", "")).lower() == "x-rapidapi-host"
        for header in draft.get("request_headers", [])
    )


def _discovered_rapidapi_host(
    draft: dict[str, Any], response: dict[str, Any], base_url: str
) -> str:
    for source in (draft, response):
        for key in ("host", "api_host", "rapidapi_host"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for header in draft.get("request_headers", []):
        if not isinstance(header, dict):
            continue
        if str(header.get("name", "")).lower() != "x-rapidapi-host":
            continue
        value = header.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return urlsplit(base_url).netloc.split("@")[-1].split(":")[0]


async def _post_json(url: str, payload: dict[str, object], *, timeout: int) -> dict[str, Any]:
    return await asyncio.to_thread(_post_json_sync, url, payload, timeout)


def _post_json_sync(url: str, payload: dict[str, object], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers=_scrapper_headers(),
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read().decode("utf-8")
            parsed = json.loads(data)
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace").strip()
        detail = response_body[:500] or "No response body."
        raise UpstreamError(
            f"Job source discovery returned HTTP {exc.code}: {detail}",
            code="job_source_discovery_upstream_error",
        ) from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise UpstreamError(
            "Job source discovery service is unavailable.",
            code="job_source_discovery_unavailable",
        ) from exc
    if not isinstance(parsed, dict):
        raise UpstreamError(
            "Job source discovery returned an invalid payload.",
            code="job_source_discovery_invalid_payload",
        )
    return parsed


def _scrapper_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if settings.SCRAPPER_API_KEY is not None:
        headers["X-Scrapper-Key"] = settings.SCRAPPER_API_KEY.get_secret_value()
    return headers


__all__ = ["DiscoveryResult", "discover_provider_config"]
