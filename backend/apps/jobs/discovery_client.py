from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from apps.core.exceptions import UpstreamError
from config.settings import get_settings


async def discover_provider_config(
    *,
    provider_slug: str,
    docs_url: str,
    known_auth_type: str | None = None,
    keywords: list[str] | None = None,
) -> dict[str, object]:
    settings = get_settings()
    payload: dict[str, object] = {
        "provider_slug": provider_slug,
        "docs_url": docs_url,
        "keywords": keywords or [],
    }
    if known_auth_type:
        payload["known_auth_type"] = known_auth_type
    return await _post_json(
        f"{settings.JOB_SOURCE_DISCOVERY_URL.rstrip('/')}/discover",
        payload,
        timeout=settings.JOB_SOURCE_DISCOVERY_TIMEOUT_SECONDS,
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


__all__ = ["discover_provider_config"]
