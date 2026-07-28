from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase

from apps.jobs.models import EvaluationClassification
from apps.pipeline.document_agent import DocumentState, generate_node
from apps.pipeline.tasks import _run_document_pipeline, _run_evaluation_pipeline


class EvaluationPipelineTests(SimpleTestCase):
    job_id = "00000000-0000-0000-0000-000000000001"

    async def test_good_fit_runs_research_and_document_generation(self) -> None:
        evaluator = AsyncMock(
            return_value=SimpleNamespace(
                error=None,
                evaluation_id="evaluation-id",
                classification=EvaluationClassification.GOOD_FIT,
            )
        )
        research = AsyncMock(return_value=SimpleNamespace(error=None, summary_id="summary-id"))
        document = AsyncMock(return_value=SimpleNamespace(error=None, document_id="document-id"))
        with (
            patch("apps.pipeline.tasks.run_evaluator_agent", evaluator),
            patch("apps.pipeline.tasks.run_research_agent", research),
            patch("apps.pipeline.tasks.run_document_agent", document),
            patch("apps.pipeline.tasks.create_notification_task.delay"),
        ):
            result = await _run_evaluation_pipeline("job-id", "user-id")

        assert result["evaluated"] is True
        assert result["researched"] is True
        assert result["documents_generated"] is True
        research.assert_awaited_once_with("job-id")
        document.assert_awaited_once_with("evaluation-id", "user-id")

    async def test_non_good_fit_stops_after_evaluation(self) -> None:
        evaluator = AsyncMock(
            return_value=SimpleNamespace(
                error=None,
                evaluation_id="evaluation-id",
                classification=EvaluationClassification.MAYBE,
            )
        )
        research = AsyncMock()
        document = AsyncMock()
        with (
            patch("apps.pipeline.tasks.run_evaluator_agent", evaluator),
            patch("apps.pipeline.tasks.run_research_agent", research),
            patch("apps.pipeline.tasks.run_document_agent", document),
            patch("apps.pipeline.tasks.create_notification_task.delay"),
        ):
            result = await _run_evaluation_pipeline("job-id", "user-id")

        assert result["evaluated"] is True
        assert result["researched"] is False
        assert result["documents_generated"] is False
        research.assert_not_awaited()
        document.assert_not_awaited()

    async def test_full_document_generation_refreshes_research(self) -> None:
        evaluation_query = MagicMock()
        evaluation_query.afirst = AsyncMock(return_value=SimpleNamespace(id="evaluation-id"))
        research = AsyncMock(return_value=SimpleNamespace(error=None, summary_id="summary-id"))
        document = AsyncMock(return_value=SimpleNamespace(error=None, document_id="document-id"))
        with (
            patch(
                "apps.pipeline.tasks.JobEvaluation.objects.filter",
                return_value=evaluation_query,
            ),
            patch("apps.pipeline.tasks.run_research_agent", research),
            patch("apps.pipeline.tasks.run_document_agent", document),
            patch("apps.pipeline.tasks.create_notification_task.delay"),
        ):
            result = await _run_document_pipeline(self.job_id, "user-id", "all")

        assert result["researched"] is True
        assert result["documents_generated"] is True
        research.assert_awaited_once_with(self.job_id)
        document.assert_awaited_once_with("evaluation-id", "user-id", "all")

    async def test_partial_document_regeneration_reuses_research(self) -> None:
        evaluation_query = MagicMock()
        evaluation_query.afirst = AsyncMock(return_value=SimpleNamespace(id="evaluation-id"))
        research = AsyncMock()
        document = AsyncMock(return_value=SimpleNamespace(error=None, document_id="document-id"))
        with (
            patch(
                "apps.pipeline.tasks.JobEvaluation.objects.filter",
                return_value=evaluation_query,
            ),
            patch("apps.pipeline.tasks.run_research_agent", research),
            patch("apps.pipeline.tasks.run_document_agent", document),
            patch("apps.pipeline.tasks.create_notification_task.delay"),
        ):
            result = await _run_document_pipeline(self.job_id, "user-id", "cv")

        assert result["researched"] is False
        assert result["documents_generated"] is True
        research.assert_not_awaited()
        document.assert_awaited_once_with("evaluation-id", "user-id", "cv")

    async def test_cv_regeneration_preserves_cover_letter(self) -> None:
        state = DocumentState(
            evaluation_id="evaluation-id",
            user_id="user-id",
            regenerate_scope="cv",
            context={
                "existing": {
                    "tailored_cv_text": "Old CV",
                    "cover_letter_text": "Original cover letter",
                }
            },
        )
        response = {
            "tailored_cv_text": "New CV",
            "quality_passed": True,
            "quality_notes": "CV checked",
        }
        llm = AsyncMock(return_value=response)
        with patch(
            "apps.pipeline.document_agent.document_llm",
            SimpleNamespace(json=llm),
        ):
            result = await generate_node(state)

        self.assertEqual(result.tailored_cv_text, "New CV")
        self.assertEqual(result.cover_letter_text, "Original cover letter")
        # pyrefly: ignore [missing-attribute]
        prompt = llm.await_args.args[0]
        self.assertIn('"tailored_cv_text": "plain text CV"', prompt)
        self.assertNotIn('"cover_letter_text": "plain text cover letter"', prompt)

    async def test_cover_letter_regeneration_preserves_cv(self) -> None:
        state = DocumentState(
            evaluation_id="evaluation-id",
            user_id="user-id",
            regenerate_scope="cover_letter",
            context={
                "existing": {
                    "tailored_cv_text": "Original CV",
                    "cover_letter_text": "Old cover letter",
                }
            },
        )
        response = {
            "cover_letter_text": "New cover letter",
            "quality_passed": True,
            "quality_notes": "Letter checked",
        }
        llm = AsyncMock(return_value=response)
        with patch(
            "apps.pipeline.document_agent.document_llm",
            SimpleNamespace(json=llm),
        ):
            result = await generate_node(state)

        self.assertEqual(result.tailored_cv_text, "Original CV")
        self.assertEqual(result.cover_letter_text, "New cover letter")
        # pyrefly: ignore [missing-attribute]
        prompt = llm.await_args.args[0]
        self.assertIn('"cover_letter_text": "plain text cover letter"', prompt)
        self.assertNotIn('"tailored_cv_text": "plain text CV"', prompt)
