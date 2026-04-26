"""Unit tests for ``jobs_service``."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.api.exceptions import ConflictError
from backend.db.models.enums import Classification
from backend.services import jobs_service


@pytest.mark.asyncio
async def test_mark_job_not_interested_conflict_when_evaluator_reject() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.dimension_scores = {"weights": {}}
    ev.final_classification = Classification.REJECT
    session = AsyncMock()

    with (
        patch(
            "backend.services.jobs_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
        pytest.raises(ConflictError) as exc,
    ):
        await jobs_service.mark_job_not_interested(session, user_id, job_id)

    assert exc.value.code == "job_already_rejected"


@pytest.mark.asyncio
async def test_mark_job_not_interested_idempotent_when_user_reject() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.final_classification = Classification.REJECT
    ev.dimension_scores = {"_kaziro": {"rejection_source": "user"}}
    session = AsyncMock()

    with (
        patch(
            "backend.services.jobs_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
    ):
        out = await jobs_service.mark_job_not_interested(session, user_id, job_id)

    assert out is ev
