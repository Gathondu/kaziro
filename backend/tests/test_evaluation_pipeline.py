from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import SimpleTestCase

from apps.jobs.models import EvaluationClassification
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
