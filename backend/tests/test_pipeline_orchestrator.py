"""Pipeline orchestrator tests (mocked stages + notifications)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

import backend.agents.pipeline_orchestrator as orch
from backend.db.models.enums import Classification


@pytest.mark.asyncio
async def test_full_pipeline_summary_mixed_outcomes() -> None:
    cfg, uid = str(uuid.uuid4()), str(uuid.uuid4())
    with (
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


def test_evaluation_concurrency_default() -> None:
    assert orch.EVALUATION_CONCURRENCY == 3
