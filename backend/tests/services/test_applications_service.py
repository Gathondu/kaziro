"""Unit tests for ``applications_service``."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.api.exceptions import ConflictError
from backend.db.models.enums import Classification
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


@pytest.mark.asyncio
async def test_create_application_promotes_reject_to_maybe_before_doc_flow() -> None:
    job_posting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.final_classification = Classification.REJECT
    ev.dimension_scores = {"_kaziro": {"rejection_source": "user"}}
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
    assert ev.final_classification is Classification.MAYBE
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_create_application_returns_existing_when_already_present() -> None:
    job_posting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    doc = MagicMock()
    doc.id = uuid.uuid4()
    existing = MagicMock()
    existing.id = uuid.uuid4()
    session = AsyncMock()

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
            return_value=doc,
        ),
        patch(
            "backend.services.applications_service.application_repository.get_by_user_posting",
            new_callable=AsyncMock,
            return_value=existing,
        ),
        patch(
            "backend.services.applications_service.application_repository.create",
            new_callable=AsyncMock,
        ) as mock_create,
    ):
        out = await applications_service.create_application(
            session, user_id, job_posting_id=job_posting_id
        )

    assert out is existing
    mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_draft_application_inserts_when_doc_and_no_application() -> None:
    job_posting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    doc = MagicMock()
    doc.id = uuid.uuid4()
    created_app = MagicMock()
    created_app.id = uuid.uuid4()
    session = AsyncMock()

    with (
        patch(
            "backend.services.applications_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
        patch(
            "backend.services.applications_service.application_doc_repository.get_by_evaluation_id",
            new_callable=AsyncMock,
            return_value=doc,
        ),
        patch(
            "backend.services.applications_service.application_repository.get_by_user_posting",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "backend.services.applications_service.application_repository.create",
            new_callable=AsyncMock,
            return_value=created_app,
        ),
        patch(
            "backend.services.applications_service.application_events_service.record_event",
            new_callable=AsyncMock,
        ),
    ):
        out = await applications_service.ensure_draft_application_after_documents(
            session, user_id, job_posting_id=job_posting_id
        )

    assert out is created_app


@pytest.mark.asyncio
async def test_ensure_draft_application_returns_existing_application() -> None:
    job_posting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ev = MagicMock()
    ev.id = uuid.uuid4()
    doc = MagicMock()
    doc.id = uuid.uuid4()
    existing = MagicMock()
    session = AsyncMock()

    with (
        patch(
            "backend.services.applications_service.evaluation_repository.get_for_user_posting",
            new_callable=AsyncMock,
            return_value=ev,
        ),
        patch(
            "backend.services.applications_service.application_doc_repository.get_by_evaluation_id",
            new_callable=AsyncMock,
            return_value=doc,
        ),
        patch(
            "backend.services.applications_service.application_repository.get_by_user_posting",
            new_callable=AsyncMock,
            return_value=existing,
        ),
    ):
        out = await applications_service.ensure_draft_application_after_documents(
            session, user_id, job_posting_id=job_posting_id
        )

    assert out is existing
