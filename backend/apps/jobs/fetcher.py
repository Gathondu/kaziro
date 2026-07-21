from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from django.db import IntegrityError

from apps.jobs.models import JobSearchConfig, JobSourceConfigDraft, RawJob
from apps.jobs.source_config import SourceProviderConfig, validate_provider_config
from config.logging import get_logger

log = get_logger(__name__)


async def fetch_jobs_for_config(config: JobSearchConfig) -> list[RawJob]:
    from apps.jobs import repositories

    drafts = await repositories.active_provider_drafts()
    stored: list[RawJob] = []
    for draft in drafts:
        source_config = validate_provider_config(draft.config)
        jobs = await asyncio.to_thread(_fetch_provider_jobs, source_config, config)
        for payload in jobs:
            external_id = _external_job_id(payload, source_config)
            if not external_id:
                log.warning(
                    "job_fetch.missing_external_id",
                    provider=draft.provider.slug,
                    job_config_id=str(config.id),
                )
                continue
            try:
                raw_job = await RawJob.objects.acreate(
                    user=config.user,
                    config=config,
                    provider=draft.provider,
                    external_job_id=external_id,
                    source_api=draft.provider.slug,
                    raw_payload=payload,
                )
                stored.append(raw_job)
            except IntegrityError:
                log.info(
                    "job_fetch.duplicate_skipped",
                    provider=draft.provider.slug,
                    external_job_id=external_id,
                )
    return stored


async def validate_draft_with_smoke_request(
    draft: JobSourceConfigDraft,
) -> tuple[bool, str, int | None, dict[str, object], list[str]]:
    source_config = validate_provider_config(draft.config)
    request_url, headers = build_request(source_config, None)
    try:
        status_code, payload = await asyncio.to_thread(_get_json, request_url, headers, 20)
    except OSError as exc:
        return False, request_url, None, {}, [str(exc)]
    jobs = _extract_jobs(payload)
    if status_code >= 400:
        return (
            False,
            request_url,
            status_code,
            {"payload_type": type(payload).__name__},
            [f"Provider returned HTTP {status_code}."],
        )
    if not jobs:
        return (
            False,
            request_url,
            status_code,
            {"payload_type": type(payload).__name__},
            ["Provider response did not contain a job-like list."],
        )
    sample = jobs[0]
    if not _external_job_id(sample, source_config):
        return (
            False,
            request_url,
            status_code,
            {"jobs_seen": len(jobs)},
            ["Sample job did not contain an external id."],
        )
    return True, request_url, status_code, {"jobs_seen": len(jobs)}, []


def build_request(
    source_config: SourceProviderConfig,
    job_config: JobSearchConfig | None,
) -> tuple[str, dict[str, str]]:
    params: dict[str, str] = {}
    query_map = source_config.query_params
    if job_config is not None:
        _set_param(params, query_map, "keywords", " ".join(job_config.keywords or []))
        _set_param(params, query_map, "location", job_config.location)
        _set_param(params, query_map, "remote_only", str(job_config.remote_only).lower())
        _set_param(params, query_map, "salary_min", job_config.salary_min)
        _set_param(params, query_map, "salary_max", job_config.salary_max)
        _set_param(
            params, query_map, "employment_types", ",".join(job_config.employment_types or [])
        )
    if source_config.pagination.page_size_param:
        params[source_config.pagination.page_size_param] = str(
            source_config.pagination.default_page_size
        )
    if source_config.pagination.type == "page" and source_config.pagination.page_param:
        params[source_config.pagination.page_param] = "1"
    if source_config.pagination.type == "offset" and source_config.pagination.page_param:
        params[source_config.pagination.page_param] = "0"

    headers: dict[str, str] = {"Accept": "application/json", "User-Agent": "Kaziro/1.0"}
    credential = os.environ.get(source_config.auth.credential_env_var or "")
    if source_config.auth.type == "bearer" and credential:
        headers["Authorization"] = f"Bearer {credential}"
    elif (
        source_config.auth.type == "static_header" and source_config.auth.header_name and credential
    ):
        headers[source_config.auth.header_name] = credential
    elif (
        source_config.auth.type == "query_param_key"
        and source_config.auth.query_param_name
        and credential
    ):
        params[source_config.auth.query_param_name] = credential

    base = str(source_config.base_url).rstrip("/")
    url = urljoin(f"{base}/", source_config.endpoint_path.lstrip("/"))
    return f"{url}?{urlencode(params)}" if params else url, headers


def _fetch_provider_jobs(
    source_config: SourceProviderConfig,
    job_config: JobSearchConfig,
) -> list[dict[str, object]]:
    request_url, headers = build_request(source_config, job_config)
    status_code, payload = _get_json(request_url, headers, 30)
    if status_code >= 400:
        raise RuntimeError(f"Provider returned HTTP {status_code}.")
    return _extract_jobs(payload)


def _get_json(url: str, headers: dict[str, str], timeout: int) -> tuple[int, object]:
    request = Request(url, method="GET", headers=headers)
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload


def _extract_jobs(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("jobs", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _external_job_id(payload: dict[str, object], source_config: SourceProviderConfig) -> str:
    candidates = [
        source_config.response_mapping.get("external_id"),
        "id",
        "job_id",
        "external_id",
        "url",
        "application_url",
    ]
    for candidate in candidates:
        if candidate and payload.get(candidate):
            return str(payload[candidate])
    return ""


def _set_param(
    params: dict[str, str],
    query_map: dict[str, str],
    logical_name: str,
    value: object,
) -> None:
    provider_name = query_map.get(logical_name)
    if provider_name and value not in (None, ""):
        params[provider_name] = str(value)


__all__ = [
    "build_request",
    "fetch_jobs_for_config",
    "validate_draft_with_smoke_request",
]
