"""Evaluator Agent — 3-pass classification of (user_profile, job_posting).

Pass 1 (``Draft``)
    First-pass numeric scoring across four dimensions (skills, seniority,
    domain, compensation) plus a free-form note.

Pass 2 (``Critic``)
    Devil's-advocate review of the draft. Returns a revised score set.
    A critic failure is non-fatal: we fall back to the draft scores so
    the pipeline never wedges on a flaky LLM call.

Pass 3 (``Judge``)
    Synthesises both passes into the final classification + user-facing
    feedback, plus an overall weighted score.

Output is upserted into ``job_evaluations`` (one row per
``(user_id, job_posting_id)``) by the persistence node.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Final, Protocol

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from backend.config import get_settings
from backend.db.models.enums import Classification
from backend.db.repositories import (
    evaluation_repository,
    job_posting_repository,
    profile_repository,
)
from backend.db.session import async_session_factory
from backend.llm.openrouter import build_chat_model
from backend.logging_config import get_logger
from backend.metrics import (
    agent_duration_seconds,
    evaluation_classification_total,
    external_api_calls_total,
    pipeline_jobs_total,
)

log = get_logger(__name__)

AGENT_NAME: Final[str] = "evaluator"

# Dimension weights (must sum to 1.0). See
# docs/design/agents/evaluator-agent.md §"Weighted scoring".
_WEIGHTS: Final[dict[str, float]] = {
    "skills_match": 0.35,
    "seniority_fit": 0.25,
    "domain_alignment": 0.25,
    "compensation_fit": 0.15,
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DimensionScores(BaseModel):
    """Four-axis scoring used by every pass."""

    skills_match: float = Field(ge=0, le=10)
    seniority_fit: float = Field(ge=0, le=10)
    domain_alignment: float = Field(ge=0, le=10)
    compensation_fit: float = Field(ge=0, le=10)

    @property
    def weighted_average(self) -> float:
        total = (
            self.skills_match * _WEIGHTS["skills_match"]
            + self.seniority_fit * _WEIGHTS["seniority_fit"]
            + self.domain_alignment * _WEIGHTS["domain_alignment"]
            + self.compensation_fit * _WEIGHTS["compensation_fit"]
        )
        return round(total, 2)


class EvaluatorState(BaseModel):
    """LangGraph state shared across all passes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_posting_id: str
    user_id: str

    # Loaded job context
    job_title: str = ""
    job_description: str = ""
    job_requirements: list[str] = Field(default_factory=list)
    job_salary_min: int | None = None
    job_salary_max: int | None = None

    # Loaded user context
    user_skills: list[str] = Field(default_factory=list)
    user_experience_years: int | None = None
    user_domain: str | None = None
    user_values: str | None = None
    user_summary: str | None = None

    # Pass 1
    pass1_scores: DimensionScores | None = None
    pass1_notes: str = ""

    # Pass 2
    pass2_critique: str = ""
    pass2_revised_scores: DimensionScores | None = None

    # Pass 3
    final_classification: Classification | None = None
    final_feedback: str = ""
    overall_score: float = 0.0

    job_evaluation_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# LLM lazy init
# ---------------------------------------------------------------------------


class _Invokable(Protocol):
    async def ainvoke(self, prompt: str) -> Any: ...


_llm: _Invokable | None = None


def _build_default_llm() -> _Invokable:
    settings = get_settings()
    return build_chat_model(
        model=settings.LLM_MODEL_EVALUATOR,
        temperature=0.2,
        settings=settings,
    )


def get_llm() -> _Invokable:
    global _llm
    if _llm is None:
        _llm = _build_default_llm()
    return _llm


def set_llm_for_tests(llm: _Invokable | None) -> None:
    global _llm
    _llm = llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_json_fence(raw: str) -> str:
    """Strip ``` / ```json fences that some chat models still emit."""
    text = raw.strip()
    if not text.startswith("```"):
        return text
    body = text.split("```", 2)
    payload = body[1] if len(body) >= 2 else text
    if payload.startswith("json"):
        payload = payload[4:]
    return payload.strip().rstrip("`").strip()


def _profile_summary(state: EvaluatorState) -> str:
    return (
        f"SKILLS: {', '.join(state.user_skills) or 'not specified'}\n"
        f"EXPERIENCE: {state.user_experience_years or 'unknown'} years\n"
        f"DOMAIN: {state.user_domain or 'not specified'}\n"
        f"PROFESSIONAL SUMMARY: {state.user_summary or 'not provided'}\n"
        f"VALUES & PREFERENCES: {state.user_values or 'not provided'}"
    )


def _job_summary(state: EvaluatorState) -> str:
    if state.job_salary_min and state.job_salary_max:
        salary = f"${state.job_salary_min:,}\u2013${state.job_salary_max:,}"
    else:
        salary = "not stated"
    requirements_block = "\n".join(
        f"  - {r}" for r in state.job_requirements[:15]
    )
    return (
        f"TITLE: {state.job_title}\n"
        f"SALARY: {salary}\n"
        f"KEY REQUIREMENTS:\n{requirements_block}\n"
        f"FULL DESCRIPTION:\n{state.job_description[:3000]}"
    )


def _scores_from_dict(data: dict[str, Any]) -> DimensionScores:
    return DimensionScores(
        skills_match=float(data["skills_match"]),
        seniority_fit=float(data["seniority_fit"]),
        domain_alignment=float(data["domain_alignment"]),
        compensation_fit=float(data["compensation_fit"]),
    )


async def _invoke_json(prompt: str) -> dict[str, Any]:
    """Send ``prompt`` to the LLM and parse the JSON body.

    Tracks every call against ``external_api_calls_total{service=openrouter}``.
    """
    try:
        response = await get_llm().ainvoke(prompt)
        external_api_calls_total.labels(service="openrouter", status="200").inc()
    except Exception:
        external_api_calls_total.labels(service="openrouter", status="error").inc()
        raise
    raw = getattr(response, "content", response)
    if not isinstance(raw, str):
        raw = str(raw)
    return json.loads(_strip_json_fence(raw))


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def load_data_node(state: EvaluatorState) -> EvaluatorState:
    """Load job + profile from the DB before any LLM call."""
    bound = log.bind(
        job_posting_id=state.job_posting_id,
        user_id=state.user_id,
        node="load_data",
    )
    bound.info("evaluator.load_start")

    async with async_session_factory() as session:
        job = await job_posting_repository.get_by_id(
            session, uuid.UUID(state.job_posting_id)
        )
        profile = await profile_repository.get_by_user_id(
            session, uuid.UUID(state.user_id)
        )

    if job is None or profile is None:
        bound.error(
            "evaluator.load_failed",
            job_found=bool(job),
            profile_found=bool(profile),
        )
        return state.model_copy(update={"error": "Job or profile not found"})

    return state.model_copy(
        update={
            "job_title": job.title,
            "job_description": job.description,
            "job_requirements": list(job.requirements or []),
            "job_salary_min": job.salary_min,
            "job_salary_max": job.salary_max,
            "user_skills": list(profile.skills or []),
            "user_experience_years": profile.experience_years,
            "user_domain": profile.domain,
            "user_values": profile.values_statement,
            "user_summary": profile.professional_summary,
        }
    )


async def pass1_draft_node(state: EvaluatorState) -> EvaluatorState:
    bound = log.bind(job_posting_id=state.job_posting_id, node="pass1_draft")
    bound.info("evaluator.pass1_start")

    prompt = f"""You are an expert career coach evaluating a job posting against a candidate's profile.

Score the job on these 4 dimensions (0-10 each):
1. skills_match       - How well do the candidate's skills match job requirements?
2. seniority_fit      - Does the experience level match the role's seniority?
3. domain_alignment   - Is the industry/domain a good match?
4. compensation_fit   - Does the salary range (if stated) align with expectations?

Be honest and critical. A score of 7+ means genuinely good for that dimension.

CANDIDATE PROFILE:
{_profile_summary(state)}

JOB POSTING:
{_job_summary(state)}

Respond in this exact JSON format (no other text):
{{
  "skills_match": <0-10>,
  "seniority_fit": <0-10>,
  "domain_alignment": <0-10>,
  "compensation_fit": <0-10>,
  "notes": "<2-3 sentences explaining your scores>"
}}"""

    try:
        data = await _invoke_json(prompt)
        scores = _scores_from_dict(data)
        bound.info(
            "evaluator.pass1_complete", weighted_avg=scores.weighted_average
        )
        return state.model_copy(
            update={
                "pass1_scores": scores,
                "pass1_notes": str(data.get("notes", "")),
            }
        )
    except Exception as exc:
        bound.error("evaluator.pass1_failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})


async def pass2_critic_node(state: EvaluatorState) -> EvaluatorState:
    bound = log.bind(job_posting_id=state.job_posting_id, node="pass2_critic")
    bound.info("evaluator.pass2_start")

    s = state.pass1_scores
    if s is None:
        # Should never trigger because of the routing guard, but stay safe.
        return state.model_copy(update={"error": "missing pass1 scores"})

    prompt = f"""You are a devil's advocate reviewing a job evaluation. Find flaws,
blind spots, and over-optimism in the initial assessment below.

INITIAL SCORES:
- Skills Match:       {s.skills_match}/10
- Seniority Fit:      {s.seniority_fit}/10
- Domain Alignment:   {s.domain_alignment}/10
- Compensation Fit:   {s.compensation_fit}/10
- Evaluator Notes:    {state.pass1_notes}

CANDIDATE PROFILE:
{_profile_summary(state)}

JOB POSTING:
{_job_summary(state)}

Provide REVISED scores (you may keep some the same if they were accurate).

Respond in this exact JSON format:
{{
  "skills_match": <0-10>,
  "seniority_fit": <0-10>,
  "domain_alignment": <0-10>,
  "compensation_fit": <0-10>,
  "critique": "<3-4 sentences explaining what the first pass missed or got right>"
}}"""

    try:
        data = await _invoke_json(prompt)
        revised = _scores_from_dict(data)
        bound.info(
            "evaluator.pass2_complete", revised_avg=revised.weighted_average
        )
        return state.model_copy(
            update={
                "pass2_revised_scores": revised,
                "pass2_critique": str(data.get("critique", "")),
            }
        )
    except Exception as exc:
        bound.warning("evaluator.pass2_failed_falling_back", error=str(exc))
        # Non-fatal: fall back to the draft scores so the Judge still runs.
        return state.model_copy(
            update={
                "pass2_revised_scores": state.pass1_scores,
                "pass2_critique": f"Critic failed: {exc}",
            }
        )


async def pass3_judge_node(state: EvaluatorState) -> EvaluatorState:
    bound = log.bind(job_posting_id=state.job_posting_id, node="pass3_judge")
    bound.info("evaluator.pass3_start")

    s1, s2 = state.pass1_scores, state.pass2_revised_scores
    if s1 is None or s2 is None:
        return state.model_copy(update={"error": "missing pass1/pass2 scores"})

    prompt = f"""You are a senior career advisor making a final decision on a job application.

You have two evaluations to synthesise:

DRAFT EVALUATION (skills={s1.skills_match}, seniority={s1.seniority_fit}, domain={s1.domain_alignment}, comp={s1.compensation_fit}):
{state.pass1_notes}

CRITIC REVISION (skills={s2.skills_match}, seniority={s2.seniority_fit}, domain={s2.domain_alignment}, comp={s2.compensation_fit}):
{state.pass2_critique}

CANDIDATE PROFILE:
{_profile_summary(state)}

JOB: {state.job_title}

Make a final CLASSIFICATION:
- GOOD_FIT:  The candidate has a strong chance. Worth applying. Weighted score >= 6.5.
- MAYBE:     Borderline. Has potential but notable gaps. Score 4.5-6.4.
- REJECT:    Poor match. Applying would be a waste of time. Score < 4.5.

Also write user-friendly feedback (3-4 sentences) explaining the decision.

Respond in this exact JSON format:
{{
  "classification": "GOOD_FIT" | "MAYBE" | "REJECT",
  "overall_score": <weighted 0-10>,
  "feedback": "<user-facing feedback>"
}}"""

    try:
        data = await _invoke_json(prompt)
        classification = Classification(str(data["classification"]))
        bound.info(
            "evaluator.pass3_complete",
            classification=classification.value,
            score=data["overall_score"],
        )
        return state.model_copy(
            update={
                "final_classification": classification,
                "final_feedback": str(data["feedback"]),
                "overall_score": float(data["overall_score"]),
            }
        )
    except Exception as exc:
        bound.error("evaluator.pass3_failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})


async def persist_evaluation_node(state: EvaluatorState) -> EvaluatorState:
    bound = log.bind(job_posting_id=state.job_posting_id, node="persist")

    if state.error or state.final_classification is None:
        pipeline_jobs_total.labels(stage="evaluate", status="failed").inc()
        bound.error("evaluator.persist_skipped_due_to_error")
        return state

    pass1 = state.pass1_scores.model_dump() if state.pass1_scores else {}
    pass2 = (
        state.pass2_revised_scores.model_dump()
        if state.pass2_revised_scores
        else {}
    )
    dimension_scores = {
        "weights": _WEIGHTS,
        "draft": pass1,
        "revised": pass2,
        "weighted_average": (
            state.pass2_revised_scores.weighted_average
            if state.pass2_revised_scores
            else None
        ),
    }

    async with async_session_factory() as session:
        evaluation = await evaluation_repository.upsert(
            session,
            user_id=uuid.UUID(state.user_id),
            job_posting_id=uuid.UUID(state.job_posting_id),
            pass1_scores=pass1,
            pass1_notes=state.pass1_notes,
            pass2_critique=state.pass2_critique,
            pass2_revised_scores=pass2,
            final_classification=state.final_classification,
            final_feedback=state.final_feedback,
            overall_score=state.overall_score,
            dimension_scores=dimension_scores,
        )
        await session.commit()
        evaluation_id = str(evaluation.id)

    evaluation_classification_total.labels(
        classification=state.final_classification.value
    ).inc()
    pipeline_jobs_total.labels(stage="evaluate", status="success").inc()
    bound.info(
        "evaluator.persisted",
        evaluation_id=evaluation_id,
        classification=state.final_classification.value,
    )
    return state.model_copy(update={"job_evaluation_id": evaluation_id})


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _route_after_load(state: EvaluatorState) -> str:
    return "error_end" if state.error else "pass1"


def _route_after_pass1(state: EvaluatorState) -> str:
    return "error_end" if state.error else "pass2"


def _route_after_pass3(state: EvaluatorState) -> str:
    return "error_end" if state.error else "persist"


def build_evaluator_graph() -> Any:
    graph = StateGraph(EvaluatorState)
    graph.add_node("load_data", load_data_node)
    graph.add_node("pass1", pass1_draft_node)
    graph.add_node("pass2", pass2_critic_node)
    graph.add_node("pass3", pass3_judge_node)
    graph.add_node("persist", persist_evaluation_node)
    graph.add_node("error_end", lambda s: s)
    graph.set_entry_point("load_data")
    graph.add_conditional_edges(
        "load_data", _route_after_load, {"pass1": "pass1", "error_end": END}
    )
    graph.add_conditional_edges(
        "pass1", _route_after_pass1, {"pass2": "pass2", "error_end": END}
    )
    graph.add_edge("pass2", "pass3")
    graph.add_conditional_edges(
        "pass3",
        _route_after_pass3,
        {"persist": "persist", "error_end": END},
    )
    graph.add_edge("persist", END)
    return graph.compile()


_graph: Any | None = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_evaluator_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def run_evaluator_agent(
    job_posting_id: str, user_id: str
) -> EvaluatorState:
    """Run the 3-pass evaluator graph for one (user, posting) pair."""
    initial = EvaluatorState(job_posting_id=job_posting_id, user_id=user_id)
    started = time.perf_counter()
    try:
        result = await _get_graph().ainvoke(initial)
    finally:
        agent_duration_seconds.labels(agent_name=AGENT_NAME).observe(
            time.perf_counter() - started
        )
    if isinstance(result, EvaluatorState):
        return result
    return EvaluatorState.model_validate(result)


__all__ = [
    "AGENT_NAME",
    "Classification",
    "DimensionScores",
    "EvaluatorState",
    "build_evaluator_graph",
    "get_llm",
    "run_evaluator_agent",
    "set_llm_for_tests",
]
