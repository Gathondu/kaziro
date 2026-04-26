"""Unit tests for ``job_evaluation_metadata`` helpers."""

from __future__ import annotations

from backend.services.job_evaluation_metadata import (
    clear_rejection_meta_for_maybe,
    merge_user_rejection_meta,
    rejection_source_from_dimension_scores,
)


def test_merge_and_read_user_rejection() -> None:
    base = {"draft": {"x": 1}}
    merged = merge_user_rejection_meta(base)
    assert merged["draft"] == {"x": 1}
    assert merged["_kaziro"]["rejection_source"] == "user"
    assert rejection_source_from_dimension_scores(merged) == "user"


def test_clear_rejection_for_maybe() -> None:
    dim = merge_user_rejection_meta({"weights": {}})
    cleared = clear_rejection_meta_for_maybe(dim)
    assert rejection_source_from_dimension_scores(cleared) is None
    assert "_kaziro" not in cleared
