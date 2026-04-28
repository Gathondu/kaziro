"""Fantastic Jobs LinkedIn RapidAPI provider implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

from backend.config import Settings
from backend.services.rapidapi_types import RapidApiQuerySpec

PROVIDER_KEY: Final[str] = "linkedin_fantastic"
SUPPORTED_HOSTS: Final[frozenset[str]] = frozenset({"linkedin-job-search-api.p.rapidapi.com"})
REFERENCE_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2] / "reference" / "linkedin_job_search_rapidapi.md"
)

ALLOWED_PATHS: Final[frozenset[str]] = frozenset(
    {
        "active-jb-24h",
        "active-jb-7d",
        "active-jb-6m",
    }
)

PATH_ALIASES: Final[dict[str, str]] = {
    "active-fts-24h": "active-jb-24h",
    "active-fts-7d": "active-jb-7d",
    "active-fts-6m": "active-jb-6m",
    "active-jobs-24h": "active-jb-24h",
    "active-jobs-7d": "active-jb-7d",
    "active-fts-24h-1": "active-jb-24h",
    "active-fts-7d-1": "active-jb-7d",
    "active-fts-24h-2": "active-jb-24h",
}

ALLOWED_QUERY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "limit",
        "offset",
        "order",
        "title_filter",
        "advanced_title_filter",
        "location_filter",
        "description_filter",
        "organization_description_filter",
        "organization_specialties_filter",
        "organization_slug_filter",
        "type_filter",
        "industry_filter",
        "seniority_filter",
        "description_type",
        "date_filter",
        "remote",
        "agency",
        "employees_lte",
        "employees_gte",
        "exclude_ats_duplicate",
        "external_apply_url",
        "directapply",
        "include_ai",
        "ai_work_arrangement_filter",
        "ai_taxonomies_a_filter",
        "ai_taxonomies_a_exclusion_filter",
        "ai_has_salary",
        "ai_experience_level_filter",
        "ai_visa_sponsorship_filter",
    }
)

LEGACY_QUERY_KEY_ALIASES: Final[dict[str, str]] = {
    "titleSearch": "title_filter",
    "locationSearch": "location_filter",
    "descriptionSearch": "description_filter",
    "descriptionType": "description_type",
    "datePostedAfter": "date_filter",
    "EmploymentTypeFilter": "type_filter",
    "seniorityFilter": "seniority_filter",
    "organizationSlugFilter": "organization_slug_filter",
    "industryFilter": "industry_filter",
    "organizationEmployeesLte": "employees_lte",
    "organizationEmployeesGte": "employees_gte",
    "excludeATSDuplicate": "exclude_ats_duplicate",
    "externalApplyUrl": "external_apply_url",
    "directApply": "directapply",
    "includeAi": "include_ai",
    "aiWorkArrangementFilter": "ai_work_arrangement_filter",
    "aiHasSalary": "ai_has_salary",
    "aiExperienceLevelFilter": "ai_experience_level_filter",
    "aiVisaSponsorshipFilter": "ai_visa_sponsorship_filter",
    "organizationDescriptionSearch": "organization_description_filter",
}


def build_system_prompt() -> str:
    return (
        "You map a user's job-search configuration to ONE Fantastic Jobs "
        "LinkedIn Job Search RapidAPI GET request. "
        "Follow ONLY the API rules in the reference. "
        "Return JSON matching the RapidApiQuerySpec schema: "
        "a path segment and query_params. "
        "Use snake_case query keys only (e.g. title_filter, location_filter, "
        "description_type, type_filter, remote, limit, offset). "
        "Build title_filter from user keywords (OR-combine distinct terms; "
        "double-quote multi-word phrases). "
        "Set location_filter when a location string is present; set remote=true "
        "when remote_only is true. "
        "Map employment_types to type_filter as a comma-separated list with no spaces "
        "(e.g. FULL_TIME,PART_TIME). "
        "Use limit equal to requested_limit from the payload. "
        "Do not invent path names — pick from the reference table (prefer active-jb-24h "
        "unless another listed path clearly fits the time window)."
    )


def _canonical_query_key(key: str) -> str:
    return LEGACY_QUERY_KEY_ALIASES.get(key, key)


def _coerce_query_value(original_key: str, canonical_key: str, value: Any) -> Any:
    if original_key == "titleSearch" and canonical_key == "title_filter":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    if original_key == "locationSearch" and canonical_key == "location_filter":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    if original_key == "descriptionSearch" and canonical_key == "description_filter":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    if original_key in {
        "EmploymentTypeFilter",
        "seniorityFilter",
        "organizationSlugFilter",
        "industryFilter",
        "aiWorkArrangementFilter",
        "aiExperienceLevelFilter",
    }:
        if isinstance(value, (list, tuple)):
            return ",".join(str(v).strip() for v in value)
        return value
    if original_key == "organizationDescriptionSearch":
        if isinstance(value, (list, tuple)):
            return " OR ".join(str(v) for v in value)
        return value
    return value


def validate_and_clamp_spec(spec: RapidApiQuerySpec, *, settings: Settings) -> RapidApiQuerySpec:
    path = spec.path.strip().lstrip("/")
    path = PATH_ALIASES.get(path, path)
    if path not in ALLOWED_PATHS:
        raise ValueError(f"rapidapi path not allowed for linkedin_fantastic: {path!r}")

    def _truthy(v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    clean: dict[str, Any] = {}
    for original_key, value in spec.query_params.items():
        if original_key == "noDirectApply":
            if _truthy(value):
                clean["directapply"] = False
            continue
        if original_key == "populateExternalApplyURL":
            if _truthy(value):
                clean["external_apply_url"] = True
            continue
        if original_key == "removeAgency":
            if _truthy(value):
                clean["agency"] = False
            continue

        canonical_key = _canonical_query_key(original_key)
        if canonical_key not in ALLOWED_QUERY_KEYS:
            continue
        clean[canonical_key] = _coerce_query_value(original_key, canonical_key, value)

    lim_raw = clean.get("limit", settings.RAPIDAPI_JOB_FETCH_LIMIT)
    try:
        lim = int(lim_raw)
    except (TypeError, ValueError):
        lim = settings.RAPIDAPI_JOB_FETCH_LIMIT
    lim = max(10, min(lim, settings.RAPIDAPI_JOB_FETCH_LIMIT))
    clean["limit"] = lim
    return RapidApiQuerySpec(path=path, query_params=clean)
