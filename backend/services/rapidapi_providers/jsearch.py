"""JSearch-specific RapidAPI query validation and prompting."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Final

from backend.config import Settings
from backend.services.rapidapi_types import RapidApiQuerySpec

PROVIDER_KEY: Final[str] = "jsearch"
SUPPORTED_HOSTS: Final[frozenset[str]] = frozenset({"jsearch.p.rapidapi.com"})
REFERENCE_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2] / "reference" / "jsearch_rapidapi.md"
)

ALLOWED_PATHS: Final[frozenset[str]] = frozenset({"search"})
PATH_ALIASES: Final[dict[str, str]] = {
    "active-fts-24h": "search",
    "active-fts-7d": "search",
    "active-fts-6m": "search",
    "active-jobs-24h": "search",
    "active-jobs-7d": "search",
    "active-jb-24h": "search",
    "active-jb-7d": "search",
    "active-jb-6m": "search",
    "jobs": "search",
}

ALLOWED_QUERY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "query",
        "page",
        "num_pages",
        "country",
        "language",
        "location",
        "date_posted",
        "work_from_home",
        "employment_types",
        "job_requirements",
        "radius",
        "exclude_job_publishers",
        "fields",
    }
)

LEGACY_QUERY_KEY_ALIASES: Final[dict[str, str]] = {
    "titleSearch": "query",
    "locationSearch": "location",
    "descriptionSearch": "query",
    "descriptionType": "fields",
    "datePostedAfter": "date_posted",
    "EmploymentTypeFilter": "employment_types",
    "type_filter": "employment_types",
    "remote": "work_from_home",
    "title_filter": "query",
    "location_filter": "location",
    "description_filter": "query",
}


def build_system_prompt() -> str:
    return (
        "You map a user's job-search configuration to ONE JSearch RapidAPI GET request. "
        "Follow ONLY the API rules in the reference. "
        "Return JSON matching the RapidApiQuerySpec schema: path + query_params. "
        "Use path 'search'. "
        "Use only JSearch keys: query,page,num_pages,country,language,location,"
        "date_posted,work_from_home,employment_types,job_requirements,radius,"
        "exclude_job_publishers,fields. "
        "Build query as natural language including role keywords and location text "
        "when present (e.g. 'data engineer jobs in berlin'). "
        "Set work_from_home=true when remote_only is true. "
        "Convert employment_types to JSearch enum values "
        "(FULLTIME,CONTRACTOR,PARTTIME,INTERN) as comma-separated string. "
        "Use page=1. "
        "Choose num_pages conservatively at 10 jobs per page, defaulting low "
        "for quota safety (cap 3 unless clearly needed). "
        "Default date_posted to 'all' unless the payload strongly implies recency."
    )


def _canonical_query_key(key: str) -> str:
    return LEGACY_QUERY_KEY_ALIASES.get(key, key)


def _coerce_query_value(original_key: str, canonical_key: str, value: Any) -> Any:
    if original_key in {"titleSearch", "title_filter"} and canonical_key == "query":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    if original_key in {"locationSearch", "location_filter"} and canonical_key == "location":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    if original_key in {"descriptionSearch", "description_filter"} and canonical_key == "query":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    if original_key in {"EmploymentTypeFilter", "type_filter"} and canonical_key == "employment_types":
        if isinstance(value, (list, tuple)):
            return ",".join(str(v).replace("_", "").strip().upper() for v in value)
        return value
    if canonical_key == "work_from_home" and isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    if canonical_key == "date_posted" and original_key == "datePostedAfter":
        return "month"
    return value


def validate_and_clamp_spec(spec: RapidApiQuerySpec, *, settings: Settings) -> RapidApiQuerySpec:
    path = spec.path.strip().lstrip("/")
    path = PATH_ALIASES.get(path, path)
    if path not in ALLOWED_PATHS:
        raise ValueError(f"rapidapi path not allowed for jsearch: {path!r}")

    def _truthy(v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    def _merge_query(existing: Any, incoming: Any) -> str:
        base = str(existing).strip() if existing else ""
        nxt = str(incoming).strip() if incoming else ""
        if base and nxt:
            return f"{base} {nxt}"
        return base or nxt

    clean: dict[str, Any] = {}
    for original_key, value in spec.query_params.items():
        if original_key == "limit":
            try:
                lim = int(value)
            except (TypeError, ValueError):
                lim = settings.RAPIDAPI_JOB_FETCH_LIMIT
            lim = max(10, min(lim, settings.RAPIDAPI_JOB_FETCH_LIMIT))
            clean["num_pages"] = max(1, min(20, math.ceil(lim / 10)))
            continue
        canonical_key = _canonical_query_key(original_key)
        if canonical_key == "work_from_home":
            if _truthy(value):
                clean["work_from_home"] = True
            continue
        if canonical_key not in ALLOWED_QUERY_KEYS:
            continue
        coerced = _coerce_query_value(original_key, canonical_key, value)
        if canonical_key == "query":
            clean["query"] = _merge_query(clean.get("query"), coerced)
            continue
        clean[canonical_key] = coerced

    page_raw = clean.get("page", 1)
    num_pages_raw = clean.get(
        "num_pages",
        max(1, min(3, math.ceil(settings.RAPIDAPI_JOB_FETCH_LIMIT / 10))),
    )
    try:
        page = int(page_raw)
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(page, 50))
    clean["page"] = page

    try:
        num_pages = int(num_pages_raw)
    except (TypeError, ValueError):
        num_pages = max(1, min(3, math.ceil(settings.RAPIDAPI_JOB_FETCH_LIMIT / 10)))
    clean["num_pages"] = max(1, min(num_pages, 20))

    if not clean.get("query"):
        clean["query"] = "software engineer jobs"

    clean.pop("limit", None)
    clean.pop("offset", None)
    return RapidApiQuerySpec(path=path, query_params=clean)

