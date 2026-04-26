"""Helpers for product metadata stored in ``JobEvaluation.dimension_scores``.

Evaluator output uses keys like ``draft`` / ``revised``; we reserve ``_kaziro``
for application-layer flags (e.g. user-initiated rejection).
"""

from __future__ import annotations

from typing import Any

_META_KEY = "_kaziro"
_USER_REJECTION = "user"


def merge_user_rejection_meta(existing: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``dimension_scores`` marking rejection as user-initiated."""
    out = dict(existing)
    meta = dict(out.get(_META_KEY) or {})
    meta["rejection_source"] = _USER_REJECTION
    out[_META_KEY] = meta
    return out


def clear_rejection_meta_for_maybe(existing: dict[str, Any]) -> dict[str, Any]:
    """Strip user-rejection metadata when promoting an evaluation to ``MAYBE``."""
    out = dict(existing)
    meta = dict(out.get(_META_KEY) or {})
    meta.pop("rejection_source", None)
    if meta:
        out[_META_KEY] = meta
    else:
        out.pop(_META_KEY, None)
    return out


def rejection_source_from_dimension_scores(dim: dict[str, Any] | None) -> str | None:
    """Return ``user`` when the user marked the job not interested; else ``None``."""
    if not dim:
        return None
    meta = dim.get(_META_KEY)
    if isinstance(meta, dict) and meta.get("rejection_source") == _USER_REJECTION:
        return _USER_REJECTION
    return None


__all__ = [
    "clear_rejection_meta_for_maybe",
    "merge_user_rejection_meta",
    "rejection_source_from_dimension_scores",
]
