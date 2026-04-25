"""Unit tests for ``applications_service``."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.api.exceptions import ConflictError
from backend.services import applications_service


@pytest.mark.asyncio
async def test_create_application_enqueues_when_no_doc() -> None:
    job_posting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    session = AsyncMock()

    mock_delay = MagicMock()
    with (
        patch(
            "backend.services.applications_service.job_posting_repository.get_by_id",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "backend.services.applications_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
        patch(
            "backend.services.applications_service.application_doc_repository.get_by_evaluation_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "backend.tasks.pipeline.run_research_then_document_for_evaluation_task",
            MagicMock(delay=mock_delay),
        ),
        pytest.raises(ConflictError) as excinfo,
    ):
        await applications_service.create_application(
            session, user_id, job_posting_id=job_posting_id
        )

    assert excinfo.value.code == "application_documents_generating"
    mock_delay.assert_called_once_with(
        str(job_posting_id),
        str(ev.id),
        str(user_id),
    )
