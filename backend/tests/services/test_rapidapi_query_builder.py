"""RapidAPI query builder (validation + httpx flattening)."""

from __future__ import annotations

import pytest
from backend.config import get_settings
from backend.services.rapidapi_query_builder import (
    RapidApiQuerySpec,
    build_get_url_and_params,
    flatten_query_params,
    validate_and_clamp_spec,
)
from pydantic import ValidationError


def test_flatten_query_params_lists_and_bool() -> None:
    pairs = flatten_query_params(
        {
            "remote": True,
            "limit": 50,
            "title_filter": ["foo", "bar"],
        }
    )
    assert ("remote", "true") in pairs
    assert ("limit", "50") in pairs
    assert pairs.count(("title_filter", "foo")) == 1
    assert pairs.count(("title_filter", "bar")) == 1


def test_validate_rejects_unknown_path() -> None:
    spec = RapidApiQuerySpec(path="unknown-endpoint", query_params={"limit": 20})
    with pytest.raises(ValueError):
        validate_and_clamp_spec(spec, settings=get_settings())


def test_validate_aliases_legacy_path_to_search(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPIDAPI_JOB_FETCH_LIMIT", "100")
    get_settings.cache_clear()
    try:
        spec = RapidApiQuerySpec(path="active-fts-24h", query_params={"limit": 10})
        out = validate_and_clamp_spec(spec, settings=get_settings())
        assert out.path == "search"
    finally:
        get_settings.cache_clear()


def test_validate_migrates_title_search_to_query() -> None:
    spec = RapidApiQuerySpec(
        path="search",
        query_params={"titleSearch": ["foo", "bar"], "limit": 10},
    )
    out = validate_and_clamp_spec(spec, settings=get_settings())
    assert out.query_params.get("query") == "foo OR bar"
    assert "titleSearch" not in out.query_params
    assert out.query_params["page"] == 1
    assert out.query_params["num_pages"] == 1


def test_validate_clamps_limit_to_settings_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPIDAPI_JOB_FETCH_LIMIT", "25")
    get_settings.cache_clear()
    try:
        spec = RapidApiQuerySpec(path="search", query_params={"limit": 9999})
        out = validate_and_clamp_spec(spec, settings=get_settings())
        assert out.query_params["num_pages"] == 3
    finally:
        get_settings.cache_clear()


def test_build_get_url_and_params_uses_host() -> None:
    spec = RapidApiQuerySpec(path="search", query_params={"num_pages": 2})
    url, pairs = build_get_url_and_params(spec, settings=get_settings())
    host = get_settings().RAPIDAPI_HOST
    assert url == f"https://{host}/search"
    assert ("num_pages", "2") in pairs


def test_rapid_api_query_spec_requires_path() -> None:
    with pytest.raises(ValidationError):
        RapidApiQuerySpec.model_validate({"query_params": {}})


def test_validate_uses_linkedin_provider_for_linkedin_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAPIDAPI_HOST", "linkedin-job-search-api.p.rapidapi.com")
    monkeypatch.setenv("RAPIDAPI_JOB_FETCH_LIMIT", "50")
    get_settings.cache_clear()
    try:
        spec = RapidApiQuerySpec(path="active-jb-24h", query_params={"limit": 999})
        out = validate_and_clamp_spec(spec, settings=get_settings())
        assert out.path == "active-jb-24h"
        assert out.query_params["limit"] == 50
    finally:
        get_settings.cache_clear()


def test_validate_rejects_unknown_rapidapi_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPIDAPI_HOST", "unknown-provider.p.rapidapi.com")
    get_settings.cache_clear()
    try:
        spec = RapidApiQuerySpec(path="search", query_params={"query": "foo"})
        with pytest.raises(ValueError):
            validate_and_clamp_spec(spec, settings=get_settings())
    finally:
        get_settings.cache_clear()
