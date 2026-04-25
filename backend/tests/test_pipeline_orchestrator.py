"""Pipeline orchestrator tests (mocked stages + notifications)."""

from __future__ import annotations

import types
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import backend.agents.pipeline_orchestrator as orch
from backend.db.models.enums import Classification


@contextmanager
def _patch_full_pipeline_user_config_gate(cfg: str, uid: str) -> Iterator[None]:
    """``run_full_pipeline_for_config`` checks user/config before work."""
    _ = cfg  # config id validated against cfg_row in production; mocks accept any
    uid_obj = uuid.UUID(uid)

    @asynccontextmanager
    async def _fake_session_cm():
        yield None

    def _factory():
        return _fake_session_cm()

    with (
        patch.object(orch, "async_session_factory", _factory),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=types.SimpleNamespace(is_active=True)),
        ),
        patch.object(
            orch.job_config_repository,
            "get_by_id_unscoped",
            new=AsyncMock(
                return_value=types.SimpleNamespace(
                    is_active=True,
                    user_id=uid_obj,
                )
            ),
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_full_pipeline_summary_mixed_outcomes() -> None:
    cfg, uid = str(uuid.uuid4()), str(uuid.uuid4())
    with (
        _patch_full_pipeline_user_config_gate(cfg, uid),
        patch.object(orch, "notify_user", new=AsyncMock()),
        patch.object(
            orch,
            "run_fetch_and_parse",
            new=AsyncMock(return_value=["posting-a", "posting-b"]),
        ),
        patch.object(
            orch,
            "run_evaluation_for_user",
            new=AsyncMock(
                side_effect=[
                    ("eval-good", Classification.GOOD_FIT),
                    ("eval-reject", Classification.REJECT),
                ]
            ),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=True)),
        patch.object(orch, "run_document_stage", new=AsyncMock(return_value=True)),
    ):
        summary = await orch.run_full_pipeline_for_config(cfg, uid)

    assert summary["jobs_parsed"] == 2
    assert summary["evaluations_good_fit"] == 1
    assert summary["evaluations_rejected"] == 1
    assert summary["documents_generated"] == 1


@pytest.mark.asyncio
async def test_full_pipeline_one_eval_failure_continues_batch() -> None:
    cfg, uid = str(uuid.uuid4()), str(uuid.uuid4())
    with (
        _patch_full_pipeline_user_config_gate(cfg, uid),
        patch.object(orch, "notify_user", new=AsyncMock()),
        patch.object(
            orch,
            "run_fetch_and_parse",
            new=AsyncMock(return_value=["p1", "p2"]),
        ),
        patch.object(
            orch,
            "run_evaluation_for_user",
            new=AsyncMock(
                side_effect=[
                    (None, None),
                    ("eval-2", Classification.GOOD_FIT),
                ]
            ),
        ),
        patch.object(orch, "run_research_stage", new=AsyncMock(return_value=True)),
        patch.object(orch, "run_document_stage", new=AsyncMock(return_value=True)),
    ):
        summary = await orch.run_full_pipeline_for_config(cfg, uid)

    assert summary["evaluations_good_fit"] == 1
    assert summary["documents_generated"] == 1


@pytest.mark.asyncio
async def test_full_pipeline_skips_when_user_inactive() -> None:
    cfg, uid = str(uuid.uuid4()), str(uuid.uuid4())
    mock_fetch = AsyncMock()
    with (
        _patch_full_pipeline_user_config_gate(cfg, uid),
        patch.object(
            orch.user_repository,
            "get_by_id",
            new=AsyncMock(return_value=types.SimpleNamespace(is_active=False)),
        ),
        patch.object(orch, "run_fetch_and_parse", new=mock_fetch),
    ):
        summary = await orch.run_full_pipeline_for_config(cfg, uid)

    assert summary["skipped_reason"] == "user_inactive_or_missing"
    assert summary["jobs_parsed"] == 0
    mock_fetch.assert_not_called()


def test_evaluation_concurrency_default() -> None:
    assert orch.EVALUATION_CONCURRENCY == 3
