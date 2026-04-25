"""Small helpers for RapidAPI HTTP retries (kept import-light for fast tests)."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx


def parse_retry_after_seconds(headers: httpx.Headers, *, status_code: int) -> float | None:
    """Parse ``Retry-After`` for 429 responses (seconds or HTTP-date)."""
    if status_code != 429:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if not raw:
        return None
    raw = raw.strip()
    if raw.isdigit():
        return float(raw)
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        wait_s = (dt - datetime.now(UTC)).total_seconds()
        if wait_s > 0:
            return wait_s
    except (TypeError, ValueError, OverflowError):
        return None
    return None


__all__ = ["parse_retry_after_seconds"]
