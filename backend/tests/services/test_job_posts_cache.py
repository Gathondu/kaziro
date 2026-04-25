"""Unit tests for job-post RapidAPI cache helpers."""

from __future__ import annotations

from backend.services.job_posts_cache import (
    cache_object_basename,
    keyword_slugs,
    normalize_keyword_slug,
    pick_best_cache_object_name,
    slug_set_from_cache_stem,
)


def test_normalize_keyword_slug_basic() -> None:
    assert normalize_keyword_slug("  Python Dev  ") == "python-dev"


def test_keyword_slugs_sorted_unique() -> None:
    assert keyword_slugs(["zebra", "apple", "apple"]) == ["apple", "zebra"]


def test_cache_object_basename_joins_with_plus_plus() -> None:
    base = cache_object_basename(["Python", "Django"])
    assert base == "django++python"


def test_pick_exact_match_wins() -> None:
    listing = [{"name": "django++python.json"}, {"name": "python++react.json"}]
    got = pick_best_cache_object_name(
        current_slugs={"python", "django"},
        exact_basename="django++python",
        listing=listing,
    )
    assert got == "django++python.json"


def test_pick_overlap_best_intersection() -> None:
    listing = [{"name": "python++react.json"}, {"name": "django++python++rust.json"}]
    got = pick_best_cache_object_name(
        current_slugs={"python", "django"},
        exact_basename="missing",
        listing=listing,
    )
    assert got == "django++python++rust.json"


def test_slug_set_from_cache_stem() -> None:
    assert slug_set_from_cache_stem("a++b") == {"a", "b"}
    assert slug_set_from_cache_stem("solo") == {"solo"}
