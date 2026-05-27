"""Unit tests for pasted job URL import."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from backend.services import job_url_import


def test_normalize_job_url_requires_http_and_preserves_query() -> None:
    normalized = job_url_import.normalize_job_url(
        " HTTPS://Jobs.Example.COM/path/to/job?gh_jid=123#section "
    )

    assert normalized == "https://jobs.example.com/path/to/job?gh_jid=123"
    assert job_url_import.manual_url_external_id(normalized).startswith("manual_url:")

    with pytest.raises(ValueError):
        job_url_import.normalize_job_url("ftp://jobs.example.com/1")
    with pytest.raises(ValueError):
        job_url_import.normalize_job_url("not a url")
    with pytest.raises(ValueError):
        job_url_import.normalize_job_url("")


@pytest.mark.asyncio
async def test_import_existing_posting_runs_single_job_pipeline() -> None:
    with (
        patch.object(
            job_url_import,
            "_posting_id_for_external_id",
            new=AsyncMock(return_value="posting-1"),
        ),
        patch.object(
            job_url_import,
            "run_pipeline_for_single_job",
            new=AsyncMock(return_value={"classification": "MAYBE"}),
        ) as pipeline,
    ):
        result = await job_url_import.import_job_url_for_user(
            "https://jobs.example.com/role",
            "00000000-0000-4000-8000-000000000001",
        )

    assert result["job_posting_id"] == "posting-1"
    pipeline.assert_awaited_once_with("posting-1", "00000000-0000-4000-8000-000000000001")


@pytest.mark.asyncio
async def test_import_new_url_scrapes_parses_then_runs_pipeline() -> None:
    class _Scraper:
        async def scrape(self, url: str, *, max_chars: int = 60_000) -> str:
            assert url == "https://jobs.example.com/role"
            return "Senior Engineer at Example Co\nApply now"

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()
    parsed = SimpleNamespace(error=None, job_posting_id="posting-2")

    with (
        patch.object(
            job_url_import,
            "_posting_id_for_external_id",
            new=AsyncMock(return_value=None),
        ),
        patch.object(job_url_import, "get_redis", return_value=redis),
        patch.object(job_url_import, "get_job_url_scraper", return_value=_Scraper()),
        patch.object(
            job_url_import,
            "_insert_or_get_raw_job",
            new=AsyncMock(return_value="raw-1"),
        ) as insert_raw,
        patch.object(job_url_import, "_raw_payload", new=AsyncMock(return_value={"x": "y"})),
        patch.object(job_url_import, "run_parser_agent", new=AsyncMock(return_value=parsed)),
        patch.object(
            job_url_import,
            "run_pipeline_for_single_job",
            new=AsyncMock(return_value={"classification": "GOOD_FIT"}),
        ) as pipeline,
    ):
        result = await job_url_import.import_job_url_for_user(
            "https://jobs.example.com/role",
            "00000000-0000-4000-8000-000000000001",
        )

    assert result["job_posting_id"] == "posting-2"
    assert insert_raw.await_count == 1
    pipeline.assert_awaited_once_with("posting-2", "00000000-0000-4000-8000-000000000001")
    redis.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_in_progress_raises_for_task_retry() -> None:
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=False)
    with (
        patch.object(job_url_import, "get_redis", return_value=redis),
        patch.object(
            job_url_import, "_wait_for_existing_posting", new=AsyncMock(return_value=None)
        ),
        pytest.raises(job_url_import.JobUrlImportInProgress),
    ):
        await job_url_import._create_posting_from_url(
            "https://jobs.example.com/role",
            "manual_url:abc",
            "00000000-0000-4000-8000-000000000001",
            SimpleNamespace(info=lambda *args, **kwargs: None),
        )


@pytest.mark.asyncio
async def test_failure_wrapper_notifies_user() -> None:
    with (
        patch.object(
            job_url_import,
            "import_job_url_for_user",
            new=AsyncMock(side_effect=job_url_import.JobUrlImportError("Could not parse.")),
        ),
        patch.object(job_url_import, "notify_user", new=AsyncMock()) as notify,
    ):
        result = await job_url_import.import_job_url_for_user_with_failure_notification(
            "https://jobs.example.com/role",
            "00000000-0000-4000-8000-000000000001",
        )

    assert result["error"] == "Could not parse."
    notify.assert_awaited_once()
    payload = notify.await_args.args[1]
    assert payload["type"] == "job_import_failed"
    assert payload["reason"] == "Could not parse."
