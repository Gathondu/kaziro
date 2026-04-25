"""Unit tests for RapidAPI Retry-After parsing."""

from __future__ import annotations

import httpx
from backend.services.rapidapi_retry_utils import parse_retry_after_seconds


def test_parse_retry_after_429_numeric() -> None:
    h = httpx.Headers({"retry-after": "42"})
    assert parse_retry_after_seconds(h, status_code=429) == 42.0


def test_parse_retry_after_non_429_ignored() -> None:
    h = httpx.Headers({"retry-after": "99"})
    assert parse_retry_after_seconds(h, status_code=500) is None


def test_parse_retry_after_missing() -> None:
    assert parse_retry_after_seconds(httpx.Headers(), status_code=429) is None
