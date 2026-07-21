from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from apps.core.exceptions import UpstreamError
from apps.jobs.source_config import validate_provider_config
from config.settings import get_settings


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
    try:
        config = validate_provider_config(draft).model_dump(mode="json")
    except ValueError as exc:
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


async def _post_json(url: str, payload: dict[str, object], *, timeout: int) -> dict[str, Any]:
    return await asyncio.to_thread(_post_json_sync, url, payload, timeout)


def _post_json_sync(url: str, payload: dict[str, object], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read().decode("utf-8")
            parsed = json.loads(data)
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


__all__ = ["DiscoveryResult", "discover_provider_config"]
