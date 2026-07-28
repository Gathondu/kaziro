from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase

from apps.applications import services as application_services
from apps.jobs import posting_services


class ApplicationWorkflowTests(SimpleTestCase):
    async def test_create_application_returns_existing_board_entry(self) -> None:
        user = SimpleNamespace(id="user-id")
        posting = SimpleNamespace(id="job-id")
        evaluation = SimpleNamespace(id="evaluation-id")
        document = SimpleNamespace(id="document-id")
        application = SimpleNamespace(id="application-id")
        evaluation_query = MagicMock()
        evaluation_query.afirst = AsyncMock(return_value=evaluation)
        document_query = MagicMock()
        document_query.afirst = AsyncMock(return_value=document)
        application_query = MagicMock()
        application_query.afirst = AsyncMock(return_value=application)
        response = SimpleNamespace(id="application-id")

        with (
            patch(
                "apps.applications.services.get_job",
                AsyncMock(return_value=posting),
            ),
            patch(
                "apps.applications.services.JobEvaluation.objects.filter",
                return_value=evaluation_query,
            ),
            patch(
                "apps.applications.services.ApplicationDoc.objects.filter",
                return_value=document_query,
            ),
            patch(
                "apps.applications.services.Application.objects.filter",
                return_value=application_query,
            ),
            patch(
                "apps.applications.services.to_response",
                AsyncMock(return_value=response),
            ) as to_response,
        ):
            result = await application_services.create_application(user, "job-id")  # type: ignore[arg-type]

        self.assertEqual(result.id, "application-id")
        to_response.assert_awaited_once_with(application, user)

    async def test_job_document_edit_rebuilds_pdfs(self) -> None:
        user = SimpleNamespace(id="user-id")
        evaluation = SimpleNamespace(id="evaluation-id")
        document = SimpleNamespace(
            tailored_cv_text="Edited CV",
            cover_letter_text="Edited letter",
            cv_pdf_path="cv.pdf",
            cover_letter_pdf_path="cover-letter.pdf",
        )
        evaluation_query = MagicMock()
        evaluation_query.afirst = AsyncMock(return_value=evaluation)
        document_query = MagicMock()
        document_query.afirst = AsyncMock(return_value=document)
        application_query = MagicMock()
        application_query.afirst = AsyncMock(return_value=None)

        with (
            patch("apps.jobs.posting_services.get_job", AsyncMock()),
            patch(
                "apps.jobs.posting_services.JobEvaluation.objects.filter",
                return_value=evaluation_query,
            ),
            patch(
                "apps.jobs.posting_services.ApplicationDoc.objects.filter",
                return_value=document_query,
            ),
            patch(
                "apps.jobs.posting_services.update_document_content",
                AsyncMock(return_value=document),
            ) as update_content,
            patch(
                "apps.applications.models.Application.objects.filter",
                return_value=application_query,
            ),
        ):
            result = await posting_services.update_documents(
                user,  # type: ignore[arg-type]
                "00000000-0000-0000-0000-000000000001",
                tailored_cv_text="Edited CV",
                cover_letter_text="Edited letter",
            )

        self.assertEqual(result.tailored_cv_text, "Edited CV")
        self.assertTrue(result.cv_pdf_available)
        update_content.assert_awaited_once_with(
            document,
            tailored_cv_text="Edited CV",
            cover_letter_text="Edited letter",
        )
