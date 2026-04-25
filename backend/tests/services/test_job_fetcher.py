"""Job fetcher: response parsing + integration smoke (no live RapidAPI)."""

from __future__ import annotations

import uuid

import pytest
from backend.db.session import async_session_factory
from backend.services.job_fetcher import extract_job_list_from_upstream, fetch_jobs_for_config
from sqlalchemy import text

pytestmark = [pytest.mark.integration]


def test_extract_job_list_accepts_list_body() -> None:
    body = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]
    assert extract_job_list_from_upstream(body) == body


def test_extract_job_list_accepts_data_key() -> None:
    body = {"data": [{"id": "x"}], "meta": 1}
    assert extract_job_list_from_upstream(body) == [{"id": "x"}]


@pytest.mark.asyncio
async def test_fetch_jobs_returns_empty_for_unknown_config_id() -> None:
    """No HTTP call: missing config short-circuits before building a client."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres unavailable: {exc}")

    bogus = str(uuid.uuid4())
    assert await fetch_jobs_for_config(bogus) == []
