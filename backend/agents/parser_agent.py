"""Parser Agent — raw upstream payload → canonical JobPosting (+ embedding).

Pipeline:

1. ``parse_node``    — LLM call (parser model, structured output) extracts
   the canonical fields from the upstream JSON. Up to ``MAX_PARSE_RETRIES``
   attempts.
2. ``embed_node``    — embeddings (OpenRouter OpenAI-compatible API) produce
   the 1536-dim
   description embedding. Embedding failure is non-fatal — we still
   persist the posting without the vector.
3. ``persist_node``  — writes a ``job_postings`` row + flips the
   ``raw_jobs`` row to ``PARSED`` (or ``FAILED``) via the repository
   layer.

The agent is deliberately the only place that constructs the LLM /
embedder. Tests inject fakes via :func:`set_llm_for_tests` /
:func:`set_embedder_for_tests`.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, date, datetime
from typing import Any, Final, Protocol, cast

from langgraph.graph import END, StateGraph
from langsmith import traceable
from pydantic import BaseModel, ConfigDict, Field

from backend.config import get_settings
from backend.db.repositories import job_posting_repository, raw_job_repository
from backend.db.session import async_session_factory
from backend.llm.openrouter import build_chat_model, build_embeddings
from backend.logging_config import get_logger
from backend.metrics import (
    agent_duration_seconds,
    external_api_calls_total,
    pipeline_jobs_total,
)

log = get_logger(__name__)

AGENT_NAME: Final[str] = "parser"
MAX_PARSE_RETRIES: Final[int] = 3


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class JobPostingSchema(BaseModel):
    """Structured representation of a parsed job posting."""

    title: str = Field(description="Job title")
    company_name: str = Field(description="Hiring company name")
    company_website: str | None = Field(default=None, description="Company website URL if present")
    location: str | None = Field(
        default=None, description="Job location (city, country, or 'Remote')"
    )
    remote_flag: bool = Field(description="True if the role is remote or hybrid")
    salary_min: int | None = Field(
        default=None, description="Minimum monthly salary in USD if stated"
    )
    salary_max: int | None = Field(
        default=None, description="Maximum monthly salary in USD if stated"
    )
    employment_type: str | None = Field(
        default=None,
        description="full-time | part-time | contract | internship",
    )
    description: str = Field(description="Full cleaned job description text")
    requirements: list[str] = Field(default_factory=list, description="Key requirements as a list")
    application_url: str = Field(description="Direct application URL")
    posted_date: str | None = Field(
        default=None, description="Date posted as YYYY-MM-DD if available"
    )


class ParserState(BaseModel):
    """LangGraph state for the Parser Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    raw_job_id: str
    raw_payload: dict[str, Any]
    parsed: JobPostingSchema | None = None
    embedding: list[float] | None = None
    job_posting_id: str | None = None
    error: str | None = None
    retries: int = 0


# ---------------------------------------------------------------------------
# LLM / embedder protocols + lazy initialisation
# ---------------------------------------------------------------------------


class _Invokable(Protocol):
    async def ainvoke(self, prompt: str) -> Any: ...


class _Embeddable(Protocol):
    async def aembed_query(self, text: str) -> list[float]: ...


_llm: _Invokable | None = None
_embedder: _Embeddable | None = None


def _build_default_llm() -> _Invokable:
    settings = get_settings()
    base = build_chat_model(
        model=settings.LLM_MODEL_PARSER,
        temperature=0,
        settings=settings,
    )
    return cast(_Invokable, base.with_structured_output(JobPostingSchema))


def _build_default_embedder() -> _Embeddable:
    return cast(_Embeddable, build_embeddings(get_settings()))


def get_llm() -> _Invokable:
    global _llm
    if _llm is None:
        _llm = _build_default_llm()
    return _llm


def get_embedder() -> _Embeddable:
    global _embedder
    if _embedder is None:
        _embedder = _build_default_embedder()
    return _embedder


def set_llm_for_tests(llm: _Invokable | None) -> None:
    global _llm
    _llm = llm


def set_embedder_for_tests(embedder: _Embeddable | None) -> None:
    global _embedder
    _embedder = embedder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_posted_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _external_id(state: ParserState) -> str:
    payload = state.raw_payload
    for key in ("job_id", "id", "jobId", "external_id"):
        candidate = payload.get(key)
        if candidate:
            return str(candidate)
    return state.raw_job_id


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def parse_node(state: ParserState) -> ParserState:
    """LLM call: extract structured fields from the raw payload."""
    bound = log.bind(raw_job_id=state.raw_job_id, node="parse")
    bound.info("parser.parse_start", attempt=state.retries + 1)

    prompt = (
        "You are a job posting parser. Extract structured information "
        "from the raw job data below.\n"
        "Return ONLY the structured fields. Do not invent data that is "
        "not present. "
        "If the salary is not stated, set the salary_min and salary_max to None. "
        "If the salary is in annual terms, convert it to monthly terms "
        " and to USD if not in USD.\n\n"
        f"RAW JOB DATA:\n{json.dumps(state.raw_payload, indent=2)}"
    )

    try:
        parsed: JobPostingSchema = await get_llm().ainvoke(prompt)
        external_api_calls_total.labels(service="openrouter", status="200").inc()
        bound.info(
            "parser.parse_success",
            title=parsed.title,
            company=parsed.company_name,
        )
        return state.model_copy(update={"parsed": parsed, "error": None})
    except Exception as exc:
        external_api_calls_total.labels(service="openrouter", status="error").inc()
        bound.warning("parser.parse_failed", error=str(exc))
        return state.model_copy(update={"error": str(exc), "retries": state.retries + 1})


async def embed_node(state: ParserState) -> ParserState:
    """Embed the description; failure is non-fatal."""
    if state.parsed is None:
        return state

    bound = log.bind(raw_job_id=state.raw_job_id, node="embed")
    bound.info("parser.embed_start")

    embed_text = f"{state.parsed.title}\n{state.parsed.company_name}\n{state.parsed.description}"

    try:
        embedding = await get_embedder().aembed_query(embed_text)
        external_api_calls_total.labels(service="openrouter", status="200").inc()
        bound.info("parser.embed_success", dims=len(embedding))
        return state.model_copy(update={"embedding": embedding})
    except Exception as exc:
        external_api_calls_total.labels(service="openrouter", status="error").inc()
        bound.warning("parser.embed_failed", error=str(exc))
        return state


async def persist_node(state: ParserState) -> ParserState:
    """Persist via the repository layer + flip the ``raw_jobs`` status."""
    bound = log.bind(raw_job_id=state.raw_job_id, node="persist")
    raw_uuid = uuid.UUID(state.raw_job_id)

    async with async_session_factory() as session:
        if state.parsed is None:
            error_text = state.error or "parse failed"
            await raw_job_repository.mark_failed(session, raw_uuid, error=error_text)
            await session.commit()
            pipeline_jobs_total.labels(stage="parse", status="failed").inc()
            bound.warning("parser.persisted_as_failed", error=error_text)
            return state

        parsed = state.parsed
        posting = await job_posting_repository.create(
            session,
            raw_job_id=raw_uuid,
            external_job_id=_external_id(state),
            title=parsed.title,
            company_name=parsed.company_name,
            company_website=parsed.company_website,
            location=parsed.location,
            remote_flag=parsed.remote_flag,
            salary_min=parsed.salary_min,
            salary_max=parsed.salary_max,
            employment_type=parsed.employment_type,
            description=parsed.description,
            requirements=parsed.requirements,
            application_url=parsed.application_url,
            posted_date=_parse_posted_date(parsed.posted_date),
            description_embedding=state.embedding,
            parsed_at=datetime.now(UTC),
        )
        await raw_job_repository.mark_parsed(session, raw_uuid)
        await session.commit()
        pipeline_jobs_total.labels(stage="parse", status="success").inc()
        bound.info("parser.persisted", job_posting_id=str(posting.id))
        return state.model_copy(update={"job_posting_id": str(posting.id)})


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _route_after_parse(state: ParserState) -> str:
    if state.error and state.retries >= MAX_PARSE_RETRIES:
        return "persist"
    if state.error:
        return "parse"
    return "embed"


def build_parser_graph() -> Any:
    graph = StateGraph(ParserState)
    graph.add_node("parse", parse_node)
    graph.add_node("embed", embed_node)
    graph.add_node("persist", persist_node)
    graph.set_entry_point("parse")
    graph.add_conditional_edges(
        "parse",
        _route_after_parse,
        {"parse": "parse", "embed": "embed", "persist": "persist"},
    )
    graph.add_edge("embed", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


_graph: Any | None = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_parser_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def _trace_parser_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    payload = inputs.get("raw_payload", {})
    keys = sorted(payload.keys())[:20] if isinstance(payload, dict) else []
    return {
        "raw_job_id": str(inputs.get("raw_job_id")),
        "raw_payload_keys": keys,
    }


def _trace_parser_outputs(output: Any) -> dict[str, Any]:
    state = output if isinstance(output, ParserState) else None
    if state is None:
        return {"output_type": type(output).__name__}
    return {
        "job_posting_id": state.job_posting_id,
        "has_error": state.error is not None,
        "retries": state.retries,
    }


@traceable(
    run_type="chain",
    name="agent.parser.run",
    tags=["agent", "parser"],
    process_inputs=_trace_parser_inputs,
    process_outputs=_trace_parser_outputs,
)
async def run_parser_agent(raw_job_id: str, raw_payload: dict[str, Any]) -> ParserState:
    """Run the parser graph for one ``raw_jobs`` row.

    LangGraph returns a plain ``dict`` (the final state ``model_dump()``);
    we re-validate so callers get a typed :class:`ParserState`.
    """
    initial = ParserState(raw_job_id=raw_job_id, raw_payload=raw_payload)
    started = time.perf_counter()
    try:
        result = await _get_graph().ainvoke(initial)
    finally:
        agent_duration_seconds.labels(agent_name=AGENT_NAME).observe(time.perf_counter() - started)
    if isinstance(result, ParserState):
        return result
    return ParserState.model_validate(result)


__all__ = [
    "AGENT_NAME",
    "MAX_PARSE_RETRIES",
    "JobPostingSchema",
    "ParserState",
    "build_parser_graph",
    "get_embedder",
    "get_llm",
    "run_parser_agent",
    "set_embedder_for_tests",
    "set_llm_for_tests",
]
