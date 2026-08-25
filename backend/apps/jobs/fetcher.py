from __future__ import annotations

import asyncio
import json
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from django.db import IntegrityError

from apps.jobs.deduplication import stable_job_external_id
from apps.jobs.models import JobSearchConfig, JobSourceConfigDraft, RawJob
from apps.jobs.source_config import (
    SourceProviderConfig,
    validate_provider_config,
)
from config.logging import get_logger
from config.settings import get_configured_env

log = get_logger(__name__)


async def fetch_jobs_for_config(config: JobSearchConfig) -> list[RawJob]:
    from apps.jobs import repositories

    drafts = await repositories.active_provider_drafts()
    stored: list[RawJob] = []
    for draft in drafts:
        source_config = validate_provider_config(draft.config)
        jobs = await asyncio.to_thread(_fetch_provider_jobs, source_config, config)
        for payload in jobs:
            upstream_id = _external_job_id(payload, source_config)
            if not upstream_id:
                log.warning(
                    "job_fetch.missing_external_id",
                    provider=draft.provider.slug,
                    job_config_id=str(config.id),
                )
                continue
            application_url = _mapped_value(
                payload,
                source_config,
                "application_url",
                ("application_url", "apply_url", "job_apply_link", "url"),
            )
            external_id = stable_job_external_id(application_url, upstream_id)
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
) -> tuple[
    bool,
    str,
    dict[str, str],
    int | None,
    dict[str, object],
    object,
    list[str],
]:
    source_config = validate_provider_config(draft.config)
    request_url, headers = build_request(
        source_config,
        None,
        provider_params=source_config.smoke_test_params,
    )
    diagnostic_url = _redact_request_url(request_url, source_config)
    diagnostic_headers = _redact_request_headers(headers, source_config)
    try:
        status_code, payload, response_headers = await asyncio.to_thread(
            _get_json, request_url, headers, 20
        )
    except OSError as exc:
        return (
            False,
            diagnostic_url,
            diagnostic_headers,
            None,
            {},
            {},
            [str(exc)],
        )
    jobs = _extract_jobs(payload, source_config)
    metadata: dict[str, object] = {
        "payload_type": type(payload).__name__,
        "response_headers": _redact_response_headers(response_headers),
    }
    if status_code >= 400:
        return (
            False,
            diagnostic_url,
            diagnostic_headers,
            status_code,
            metadata,
            payload,
            [f"Provider returned HTTP {status_code}."],
        )
    if not jobs:
        return (
            False,
            diagnostic_url,
            diagnostic_headers,
            status_code,
            metadata,
            payload,
            ["Provider response did not contain a job-like list."],
        )
    metadata["jobs_seen"] = len(jobs)
    sample = jobs[0]
    if not _external_job_id(sample, source_config):
        return (
            False,
            diagnostic_url,
            diagnostic_headers,
            status_code,
            metadata,
            payload,
            ["Sample job did not contain an external id."],
        )
    return (
        True,
        diagnostic_url,
        diagnostic_headers,
        status_code,
        metadata,
        payload,
        [],
    )


def build_request(
    source_config: SourceProviderConfig,
    job_config: JobSearchConfig | None,
    *,
    provider_params: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    params: dict[str, str] = dict(provider_params or {})
    query_map = source_config.query_params
    if job_config is not None:
        _set_param(params, query_map, "keywords", " ".join(job_config.keywords or []))
        _set_param(params, query_map, "location", job_config.location)
        _set_param(
            params,
            query_map,
            "remote_only",
            str(job_config.remote_only).lower(),
        )
        _set_param(params, query_map, "salary_min", job_config.salary_min)
        _set_param(params, query_map, "salary_max", job_config.salary_max)
        _set_param(
            params,
            query_map,
            "employment_types",
            ",".join(job_config.employment_types or []),
        )
    if source_config.pagination.page_size_param:
        params[source_config.pagination.page_size_param] = str(
            source_config.pagination.default_page_size
        )
    if source_config.pagination.type == "page" and source_config.pagination.page_param:
        params[source_config.pagination.page_param] = "1"
    if source_config.pagination.type == "offset" and source_config.pagination.page_param:
        params[source_config.pagination.page_param] = "0"

    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "Kaziro/1.0",
    }
    for configured_header in source_config.request_headers:
        header_value = configured_header.value
        if (
            _is_rapidapi(source_config)
            and configured_header.name.lower() == "x-rapidapi-host"
            and configured_header.value_env_var
        ):
            header_value = urlsplit(str(source_config.base_url)).netloc.split("@")[-1].split(":")[0]
        elif configured_header.value_env_var:
            header_value = get_configured_env(configured_header.value_env_var)
        if header_value:
            headers[configured_header.name] = header_value

    credential_env_var = (
        "RAPIDAPI_KEY"
        if _is_rapidapi(source_config) and source_config.auth.type != "none"
        else source_config.auth.credential_env_var or ""
    )
    credential = get_configured_env(credential_env_var)
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
    status_code, payload, _ = _get_json(request_url, headers, 30)
    if status_code >= 400:
        raise RuntimeError(f"Provider returned HTTP {status_code}.")
    return _extract_jobs(payload, source_config)


def _get_json(
    url: str, headers: dict[str, str], timeout: int
) -> tuple[int, object, dict[str, str]]:
    request = Request(url, method="GET", headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = _decode_response_payload(response.read())
            return response.status, payload, dict(response.headers.items())
    except HTTPError as exc:
        payload = _decode_response_payload(exc.read())
        return exc.code, payload, dict(exc.headers.items())


def _decode_response_payload(body: bytes) -> object:
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _redact_request_url(url: str, source_config: SourceProviderConfig) -> str:
    secret_param = (
        source_config.auth.query_param_name
        if source_config.auth.type == "query_param_key"
        else None
    )
    if not secret_param:
        return url
    parsed = urlsplit(url)
    query = [
        (key, "<redacted>" if key == secret_param else value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


def _redact_request_headers(
    headers: dict[str, str], source_config: SourceProviderConfig
) -> dict[str, str]:
    secret_names = {
        configured.name.lower()
        for configured in source_config.request_headers
        if configured.value_env_var
    }
    if source_config.auth.type == "bearer":
        secret_names.add("authorization")
    if source_config.auth.type == "static_header" and source_config.auth.header_name:
        secret_names.add(source_config.auth.header_name.lower())
    return {
        name: "<redacted>" if name.lower() in secret_names else value
        for name, value in headers.items()
    }


def _redact_response_headers(headers: dict[str, str]) -> dict[str, str]:
    secret_names = {"authorization", "proxy-authorization", "set-cookie"}
    return {
        name: "<redacted>" if name.lower() in secret_names else value
        for name, value in headers.items()
    }


def _extract_jobs(payload: object, source_config: SourceProviderConfig) -> list[dict[str, object]]:
    if source_config.response_list_path:
        configured_value = _resolve_response_path(payload, source_config.response_list_path)
        if isinstance(configured_value, list):
            return [item for item in configured_value if isinstance(item, dict)]

    return _find_job_list(payload)


def _resolve_response_path(payload: object, path: str) -> object:
    value = payload
    for segment in path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return None
        value = value[segment]
    return value


def _find_job_list(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("jobs", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        for key in ("data", "response", "result"):
            value = payload.get(key)
            if isinstance(value, dict):
                jobs = _find_job_list(value)
                if jobs:
                    return jobs
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


def _mapped_value(
    payload: dict[str, object],
    source_config: SourceProviderConfig,
    logical_name: str,
    fallback_keys: tuple[str, ...],
) -> object:
    configured_path = source_config.response_mapping.get(logical_name)
    if configured_path:
        value = _resolve_response_path(payload, configured_path)
        if value not in (None, ""):
            return value
    return next(
        (payload[key] for key in fallback_keys if payload.get(key) not in (None, "")),
        "",
    )


def _set_param(
    params: dict[str, str],
    query_map: dict[str, str],
    logical_name: str,
    value: object,
) -> None:
    provider_name = query_map.get(logical_name)
    if provider_name and value not in (None, ""):
        params[provider_name] = str(value)


def _is_rapidapi(source_config: SourceProviderConfig) -> bool:
    if "rapidapi.com" in urlsplit(str(source_config.base_url)).netloc.lower():
        return True
    if (
        source_config.auth.header_name
        and source_config.auth.header_name.lower() == "x-rapidapi-key"
    ):
        return True
    return any(header.name.lower() == "x-rapidapi-host" for header in source_config.request_headers)


__all__ = [
    "build_request",
    "fetch_jobs_for_config",
    "validate_draft_with_smoke_request",
]
