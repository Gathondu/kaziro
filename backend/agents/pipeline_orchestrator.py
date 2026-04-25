"""Pipeline Orchestrator — fetch → parse → evaluate → research → document.

Coordinates the full agentic pipeline for one ``(JobSearchConfig, user)``
pair, plus a single-job entrypoint for manual API triggers.

Design rules (see ``docs/architecture/04-pipeline.md``):

* The fetcher already inserts ``raw_jobs`` rows + dedupes — we never
  manually persist raw rows here.
* The parser persists ``job_postings`` and flips the raw row state — we
  re-read the posting id by ``raw_job_id``.
* Evaluator/Research/Document are wrapped per-user with try/except so
  one user's failure cannot poison another.
* User-facing notifications are best-effort (Pub/Sub).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from langsmith import traceable

from backend.agents.document_agent import run_document_agent
from backend.agents.evaluator_agent import run_evaluator_agent
from backend.agents.parser_agent import run_parser_agent
from backend.agents.research_agent import run_research_agent
from backend.db.models.enums import Classification
from backend.db.repositories import (
    evaluation_repository,
    job_config_repository,
    job_posting_repository,
    raw_job_repository,
    user_repository,
)
from backend.db.session import async_session_factory
from backend.logging_config import get_logger
from backend.metrics import active_pipeline_tasks
from backend.services.job_fetcher import JobFetchError, fetch_jobs_for_config
from backend.services.notifications import notify_user

log = get_logger(__name__)

EVALUATION_CONCURRENCY: Final[int] = 3


def _trace_pipeline_basic_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "config_id": str(inputs.get("config_id")) if "config_id" in inputs else None,
        "job_posting_id": str(inputs.get("job_posting_id"))
        if "job_posting_id" in inputs
        else None,
        "job_evaluation_id": str(inputs.get("job_evaluation_id"))
        if "job_evaluation_id" in inputs
        else None,
        "user_id": str(inputs.get("user_id")) if "user_id" in inputs else None,
    }


def _trace_pipeline_outputs(output: Any) -> dict[str, Any]:
    if isinstance(output, list):
        return {"len": len(output)}
    if isinstance(output, tuple):
        return {"tuple_len": len(output)}
    if isinstance(output, dict):
        return {"keys": sorted(output.keys())}
    if isinstance(output, bool):
        return {"ok": output}
    return {"output_type": type(output).__name__}


# ---------------------------------------------------------------------------
# Stage 1: Fetch + Parse
# ---------------------------------------------------------------------------


@traceable(
    run_type="chain",
    name="pipeline.run_fetch_and_parse",
    tags=["pipeline", "fetch_parse"],
    process_inputs=_trace_pipeline_basic_inputs,
    process_outputs=_trace_pipeline_outputs,
)
async def run_fetch_and_parse(
    config_id: str, user_id: str
) -> list[str]:
    """Fetch + parse new jobs for a config; return parsed posting ids."""
    bound = log.bind(config_id=config_id, user_id=user_id, stage="fetch_parse")
    bound.info("pipeline.fetch_start")

    try:
        new_payloads = await fetch_jobs_for_config(config_id)
    except JobFetchError as exc:
        bound.error("pipeline.fetch_failed", error=str(exc))
        return []

    if not new_payloads:
        bound.info("pipeline.no_new_jobs")
        return []

    # The fetcher inserted the raw rows; pull their ids back so we can
    # invoke the parser. We refilter by ``user_id`` (which the fetcher
    # used during insert) and restrict to PENDING.
    parsed_posting_ids: list[str] = []
    user_uuid = uuid.UUID(user_id)

    async with async_session_factory() as session:
        pending = await raw_job_repository.list_pending(
            session, limit=len(new_payloads) * 2
        )
        # Only operate on rows that belong to this user — list_pending
        # returns global pending rows, so filter here for safety.
        pending = [row for row in pending if row.user_id == user_uuid]

    for raw in pending:
        try:
            await run_parser_agent(str(raw.id), raw.raw_payload)
        except Exception as exc:
            bound.error(
                "pipeline.parser_exception",
                raw_job_id=str(raw.id),
                error=str(exc),
            )
            continue
        async with async_session_factory() as session:
            posting = await _posting_for_raw(session, raw.id)
        if posting is not None:
            parsed_posting_ids.append(str(posting.id))

    bound.info(
        "pipeline.parse_complete",
        attempted=len(pending),
        parsed=len(parsed_posting_ids),
    )
    return parsed_posting_ids


async def _posting_for_raw(session: Any, raw_job_id: uuid.UUID) -> Any:
    from sqlalchemy import select

    from backend.db.models.job_posting import JobPosting

    stmt = select(JobPosting).where(JobPosting.raw_job_id == raw_job_id)
    return (await session.execute(stmt)).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Stage 2: Evaluate
# ---------------------------------------------------------------------------


@traceable(
    run_type="chain",
    name="pipeline.run_evaluation_for_user",
    tags=["pipeline", "evaluate"],
    process_inputs=_trace_pipeline_basic_inputs,
    process_outputs=_trace_pipeline_outputs,
)
async def run_evaluation_for_user(
    job_posting_id: str, user_id: str
) -> tuple[str | None, Classification | None]:
    """Run the evaluator graph for one (posting, user) pair.

    Returns ``(evaluation_id, classification)`` so the orchestrator can
    decide whether to escalate to Research/Document.
    """
    bound = log.bind(
        job_posting_id=job_posting_id, user_id=user_id, stage="evaluate"
    )
    bound.info("pipeline.evaluation_start")

    try:
        result = await run_evaluator_agent(job_posting_id, user_id)
    except Exception as exc:
        bound.error("pipeline.evaluation_exception", error=str(exc))
        return None, None

    if result.error:
        bound.error("pipeline.evaluation_error", error=result.error)
        return None, None

    classification = result.final_classification
    bound.info(
        "pipeline.evaluation_complete",
        classification=classification.value if classification else None,
        score=result.overall_score,
    )

    await notify_user(
        user_id,
        {
            "type": "evaluation_complete",
            "job_posting_id": job_posting_id,
            "classification": (
                classification.value if classification else None
            ),
            "score": result.overall_score,
        },
    )

    return result.job_evaluation_id, classification


# ---------------------------------------------------------------------------
# Stage 3: Research
# ---------------------------------------------------------------------------


@traceable(
    run_type="chain",
    name="pipeline.run_research_stage",
    tags=["pipeline", "research"],
    process_inputs=_trace_pipeline_basic_inputs,
    process_outputs=_trace_pipeline_outputs,
)
async def run_research_stage(job_posting_id: str, user_id: str) -> bool:
    bound = log.bind(
        job_posting_id=job_posting_id, user_id=user_id, stage="research"
    )
    bound.info("pipeline.research_start")
    try:
        result = await run_research_agent(job_posting_id)
    except Exception as exc:
        bound.error("pipeline.research_exception", error=str(exc))
        return False
    if result.error:
        bound.error("pipeline.research_error", error=result.error)
        return False
    bound.info("pipeline.research_complete", skipped=result.skipped)
    return True


# ---------------------------------------------------------------------------
# Stage 4: Document
# ---------------------------------------------------------------------------


@traceable(
    run_type="chain",
    name="pipeline.run_document_stage",
    tags=["pipeline", "document"],
    process_inputs=_trace_pipeline_basic_inputs,
    process_outputs=_trace_pipeline_outputs,
)
async def run_document_stage(job_evaluation_id: str, user_id: str) -> bool:
    bound = log.bind(
        job_evaluation_id=job_evaluation_id, user_id=user_id, stage="document"
    )
    bound.info("pipeline.document_start")
    try:
        result = await run_document_agent(job_evaluation_id, user_id)
    except Exception as exc:
        bound.error("pipeline.document_exception", error=str(exc))
        return False
    if result.error:
        bound.error("pipeline.document_error", error=result.error)
        return False

    await notify_user(
        user_id,
        {
            "type": "documents_ready",
            "job_evaluation_id": job_evaluation_id,
            "application_doc_id": result.application_doc_id,
            "quality_passed": result.quality_passed,
        },
    )
    bound.info("pipeline.document_complete", quality_passed=result.quality_passed)
    return True


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


@traceable(
    run_type="chain",
    name="pipeline.run_full_pipeline_for_config",
    tags=["pipeline", "full"],
    process_inputs=_trace_pipeline_basic_inputs,
    process_outputs=_trace_pipeline_outputs,
)
async def run_full_pipeline_for_config(
    config_id: str, user_id: str
) -> dict[str, Any]:
    """Fetch → parse → evaluate (concurrent) → research+docs (sequential).

    Used by the Celery beat task. Returns a summary dict suitable for
    structured logging + observability assertions.
    """
    bound = log.bind(config_id=config_id, user_id=user_id)
    bound.info("pipeline.full_start")

    summary: dict[str, Any] = {
        "config_id": config_id,
        "user_id": user_id,
        "started_at": datetime.now(UTC).isoformat(),
        "jobs_parsed": 0,
        "evaluations_good_fit": 0,
        "evaluations_maybe": 0,
        "evaluations_rejected": 0,
        "documents_generated": 0,
        "errors": [],
    }

    cfg_uuid = uuid.UUID(str(config_id))
    uid = uuid.UUID(str(user_id))
    async with async_session_factory() as gate_session:
        user_row = await user_repository.get_by_id(gate_session, uid)
        cfg_row = await job_config_repository.get_by_id_unscoped(gate_session, cfg_uuid)
    if user_row is None or not user_row.is_active:
        bound.info("pipeline.full_skipped", reason="user_inactive_or_missing")
        summary["skipped_reason"] = "user_inactive_or_missing"
        summary["completed_at"] = datetime.now(UTC).isoformat()
        return summary
    if (
        cfg_row is None
        or not cfg_row.is_active
        or cfg_row.user_id != uid
    ):
        bound.info("pipeline.full_skipped", reason="config_inactive_or_mismatch")
        summary["skipped_reason"] = "config_inactive_or_mismatch"
        summary["completed_at"] = datetime.now(UTC).isoformat()
        return summary

    active_pipeline_tasks.inc()
    try:
        parsed_ids = await run_fetch_and_parse(config_id, user_id)
        summary["jobs_parsed"] = len(parsed_ids)
        if not parsed_ids:
            summary["completed_at"] = datetime.now(UTC).isoformat()
            return summary

        semaphore = asyncio.Semaphore(EVALUATION_CONCURRENCY)

        async def _evaluate_one(
            posting_id: str,
        ) -> tuple[str, str | None, Classification | None]:
            async with semaphore:
                ev_id, cls = await run_evaluation_for_user(posting_id, user_id)
                return posting_id, ev_id, cls

        results = await asyncio.gather(*(_evaluate_one(p) for p in parsed_ids))

        good_fit: list[tuple[str, str]] = []  # (posting_id, evaluation_id)
        for posting_id, ev_id, classification in results:
            if classification is Classification.GOOD_FIT:
                summary["evaluations_good_fit"] += 1
                if ev_id is not None:
                    good_fit.append((posting_id, ev_id))
            elif classification is Classification.MAYBE:
                summary["evaluations_maybe"] += 1
            elif classification is Classification.REJECT:
                summary["evaluations_rejected"] += 1

        for posting_id, evaluation_id in good_fit:
            research_ok = await run_research_stage(posting_id, user_id)
            if not research_ok:
                continue
            doc_ok = await run_document_stage(evaluation_id, user_id)
            if doc_ok:
                summary["documents_generated"] += 1
    finally:
        active_pipeline_tasks.dec()

    summary["completed_at"] = datetime.now(UTC).isoformat()
    bound.info("pipeline.full_complete", **{
        k: v for k, v in summary.items() if k != "errors"
    })
    return summary


@traceable(
    run_type="chain",
    name="pipeline.run_pipeline_for_single_job",
    tags=["pipeline", "single_job"],
    process_inputs=_trace_pipeline_basic_inputs,
    process_outputs=_trace_pipeline_outputs,
)
async def run_pipeline_for_single_job(
    job_posting_id: str, user_id: str
) -> dict[str, Any]:
    """Manual single-job entrypoint (admin/API trigger)."""
    user_uuid = uuid.UUID(user_id)
    posting_uuid = uuid.UUID(job_posting_id)

    async with async_session_factory() as session:
        user_row = await user_repository.get_by_id(session, user_uuid)
        if user_row is None or not user_row.is_active:
            return {
                "job_posting_id": job_posting_id,
                "error": "user_inactive_or_missing",
            }
        posting = await job_posting_repository.get_by_id(session, posting_uuid)
        if posting is None:
            return {"error": "Job posting not found"}

    eval_id, classification = await run_evaluation_for_user(
        job_posting_id, user_id
    )
    if eval_id is None or classification is None:
        return {
            "job_posting_id": job_posting_id,
            "error": "Evaluation failed",
        }

    if classification is Classification.REJECT:
        return {
            "job_posting_id": job_posting_id,
            "evaluation_id": eval_id,
            "classification": classification.value,
            "research_completed": False,
            "documents_generated": False,
        }

    research_ok = await run_research_stage(job_posting_id, user_id)
    docs_ok = (
        await run_document_stage(eval_id, user_id) if research_ok else False
    )

    # Echo back the latest dimension snapshot (handy for the API response).
    async with async_session_factory() as session:
        evaluation = await evaluation_repository.get_by_id(
            session, user_uuid, uuid.UUID(eval_id)
        )

    return {
        "job_posting_id": job_posting_id,
        "evaluation_id": eval_id,
        "classification": classification.value,
        "overall_score": float(evaluation.overall_score) if evaluation else None,
        "research_completed": research_ok,
        "documents_generated": docs_ok,
    }


__all__ = [
    "EVALUATION_CONCURRENCY",
    "run_document_stage",
    "run_evaluation_for_user",
    "run_fetch_and_parse",
    "run_full_pipeline_for_config",
    "run_pipeline_for_single_job",
    "run_research_stage",
]
