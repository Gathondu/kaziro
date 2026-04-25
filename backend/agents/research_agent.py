"""Research Agent — scrape (company website + job page) → company brief.

Runs only after the Evaluator classifies a posting as ``GOOD_FIT``.

Pipeline:

1. ``check_cache_node``    — short-circuit if a fresh row exists in
   ``company_summaries`` (TTL 30 days).
2. ``scrape_node``         — Firecrawl scrape of company site + job
   listing page (in parallel). Failures are non-fatal — the brief
   downgrades gracefully when content is missing.
3. ``generate_brief_node`` — LLM synthesis into a structured brief.
4. ``persist_summary_node``— ``company_summary_repository.upsert`` writes
   the row + 30-day TTL.

Tests inject fakes for the LLM (``set_llm_for_tests``) and for the
Firecrawl client (``set_firecrawl_client_for_tests``).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Final, Protocol, cast

import httpx
from langgraph.graph import END, StateGraph
from langsmith import traceable
from pydantic import BaseModel, ConfigDict

from backend.config import get_settings
from backend.db.repositories import (
    company_summary_repository,
    job_posting_repository,
)
from backend.db.session import async_session_factory
from backend.llm.openrouter import build_chat_model
from backend.logging_config import get_logger
from backend.metrics import (
    agent_duration_seconds,
    external_api_calls_total,
    pipeline_jobs_total,
)

log = get_logger(__name__)

AGENT_NAME: Final[str] = "research"

DEFAULT_FIRECRAWL_BASE: Final[str] = "https://api.firecrawl.dev/v1"
SCRAPE_MAX_CHARS: Final[int] = 8000
BRIEF_INPUT_MAX_CHARS: Final[int] = 10_000


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ResearchState(BaseModel):
    """LangGraph state for the Research Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_posting_id: str
    company_name: str = ""
    company_website: str | None = None
    application_url: str = ""
    job_title: str = ""

    website_content: str = ""
    job_page_content: str = ""

    mission: str = ""
    values: str = ""
    culture: str = ""
    tech_stack: str = ""
    team_size_approx: str = ""
    recent_news: str = ""
    ai_summary: str = ""

    summary_id: str | None = None
    error: str | None = None
    skipped: bool = False


# ---------------------------------------------------------------------------
# Pluggable Firecrawl client
# ---------------------------------------------------------------------------


class FirecrawlClient(Protocol):
    async def scrape(self, url: str, *, max_chars: int = SCRAPE_MAX_CHARS) -> str: ...


class _DefaultFirecrawlClient:
    """Real Firecrawl HTTP client. Failures are swallowed → empty string."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self._base = (
            str(settings.FIRECRAWL_BASE_URL)
            if settings.FIRECRAWL_BASE_URL
            else (base_url or DEFAULT_FIRECRAWL_BASE)
        ).rstrip("/")
        self._headers = {
            "Authorization": (
                f"Bearer {settings.FIRECRAWL_API_KEY.get_secret_value()}"
            ),
            "Content-Type": "application/json",
        }

    async def scrape(
        self, url: str, *, max_chars: int = SCRAPE_MAX_CHARS
    ) -> str:
        bound = log.bind(url=url)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._base}/scrape",
                    headers=self._headers,
                    json={
                        "url": url,
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                    },
                )
        except httpx.RequestError as exc:
            external_api_calls_total.labels(
                service="firecrawl", status="network_error"
            ).inc()
            bound.warning("firecrawl.network_error", error=str(exc))
            return ""

        external_api_calls_total.labels(
            service="firecrawl", status=str(resp.status_code)
        ).inc()
        if resp.status_code >= 400:
            bound.warning(
                "firecrawl.scrape_failed",
                status=resp.status_code,
                body=resp.text[:200],
            )
            return ""
        try:
            data = resp.json()
        except ValueError:
            bound.warning("firecrawl.invalid_json")
            return ""
        content = ""
        payload = data.get("data") if isinstance(data, dict) else None
        if isinstance(payload, dict):
            content = str(payload.get("markdown", "") or "")
        elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
            content = str(payload[0].get("markdown", "") or "")
        bound.info("firecrawl.scrape_success", chars=len(content))
        return content[:max_chars]


_firecrawl_client: FirecrawlClient | None = None


def get_firecrawl_client() -> FirecrawlClient:
    global _firecrawl_client
    if _firecrawl_client is None:
        _firecrawl_client = _DefaultFirecrawlClient()
    return _firecrawl_client


def set_firecrawl_client_for_tests(client: FirecrawlClient | None) -> None:
    global _firecrawl_client
    _firecrawl_client = client


# ---------------------------------------------------------------------------
# Pluggable LLM
# ---------------------------------------------------------------------------


class _Invokable(Protocol):
    async def ainvoke(self, prompt: str) -> Any: ...


_llm: _Invokable | None = None


def _build_default_llm() -> _Invokable:
    settings = get_settings()
    return cast(
        _Invokable,
        build_chat_model(
            model=settings.LLM_MODEL_RESEARCH,
            temperature=0.3,
            settings=settings,
        ),
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


def _strip_json_fence(text: str) -> str:
    body = text.strip()
    if not body.startswith("```"):
        return body
    parts = body.split("```", 2)
    payload = parts[1] if len(parts) >= 2 else body
    if payload.startswith("json"):
        payload = payload[4:]
    return payload.strip().rstrip("`").strip()


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def check_cache_node(state: ResearchState) -> ResearchState:
    bound = log.bind(job_posting_id=state.job_posting_id, node="check_cache")
    bound.info("research.cache_check_start")

    posting_uuid = uuid.UUID(state.job_posting_id)
    async with async_session_factory() as session:
        job = await job_posting_repository.get_by_id(session, posting_uuid)
        if job is None:
            return state.model_copy(update={"error": "Job posting not found"})

        cached = await company_summary_repository.get_active_for_posting(
            session, posting_uuid
        )

    if cached is not None:
        bound.info(
            "research.cache_hit",
            summary_id=str(cached.id),
            expires_at=cached.expires_at.isoformat(),
        )
        return state.model_copy(
            update={
                "skipped": True,
                "summary_id": str(cached.id),
                "company_name": cached.company_name,
                "mission": cached.mission or "",
                "values": cached.values or "",
                "culture": cached.culture or "",
                "tech_stack": cached.tech_stack or "",
                "team_size_approx": cached.team_size_approx or "",
                "recent_news": cached.recent_news or "",
                "ai_summary": cached.ai_summary or "",
            }
        )

    return state.model_copy(
        update={
            "company_name": job.company_name,
            "company_website": job.company_website,
            "application_url": job.application_url,
            "job_title": job.title,
        }
    )


async def scrape_node(state: ResearchState) -> ResearchState:
    if state.skipped or state.error:
        return state

    bound = log.bind(company=state.company_name, node="scrape")
    bound.info("research.scrape_start")

    client = get_firecrawl_client()
    coroutines: list[Any] = []
    coroutines.append(
        client.scrape(state.company_website) if state.company_website else _empty()
    )
    coroutines.append(
        client.scrape(state.application_url) if state.application_url else _empty()
    )

    raw_results = await asyncio.gather(*coroutines, return_exceptions=True)
    website_content = _coerce_str(raw_results[0])
    job_page_content = _coerce_str(raw_results[1])

    if not website_content and not job_page_content:
        bound.warning("research.no_content_scraped")

    return state.model_copy(
        update={
            "website_content": website_content,
            "job_page_content": job_page_content,
        }
    )


async def _empty() -> str:
    return ""


def _coerce_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


async def generate_brief_node(state: ResearchState) -> ResearchState:
    if state.skipped or state.error:
        return state

    bound = log.bind(company=state.company_name, node="generate_brief")
    bound.info("research.brief_generation_start")

    combined = (
        f"=== COMPANY WEBSITE ===\n{state.website_content}\n\n"
        f"=== JOB POSTING PAGE ===\n{state.job_page_content}"
    )

    prompt = f"""You are a company research analyst helping a job applicant prepare for an application.

Analyse the content below and extract structured information about the company.
If information is not present, state "Not available" rather than guessing.

COMPANY: {state.company_name}
ROLE: {state.job_title}

SCRAPED CONTENT:
{combined[:BRIEF_INPUT_MAX_CHARS]}

Provide a structured analysis in this exact JSON format (no other text):
{{
  "mission": "<company mission statement or core purpose, 1-2 sentences>",
  "values": "<company values, comma-separated>",
  "culture": "<description of company culture, 2-3 sentences>",
  "tech_stack": "<technologies used, if detectable>",
  "team_size_approx": "<approximate team/company size if mentioned>",
  "recent_news": "<notable recent news, funding, launches — or Not available>",
  "ai_summary": "<a comprehensive 4-5 sentence brief>"
}}"""

    try:
        response = await get_llm().ainvoke(prompt)
        external_api_calls_total.labels(service="openrouter", status="200").inc()
    except Exception as exc:
        external_api_calls_total.labels(service="openrouter", status="error").inc()
        bound.error("research.brief_generation_failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})

    raw = getattr(response, "content", response)
    if not isinstance(raw, str):
        raw = str(raw)

    try:
        data = json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError as exc:
        bound.error(
            "research.brief_parse_failed", error=str(exc), preview=raw[:200]
        )
        return state.model_copy(update={"error": f"brief parse error: {exc}"})

    bound.info("research.brief_generated")
    return state.model_copy(
        update={
            "mission": str(data.get("mission", "")),
            "values": str(data.get("values", "")),
            "culture": str(data.get("culture", "")),
            "tech_stack": str(data.get("tech_stack", "")),
            "team_size_approx": str(data.get("team_size_approx", "")),
            "recent_news": str(data.get("recent_news", "")),
            "ai_summary": str(data.get("ai_summary", "")),
        }
    )


async def persist_summary_node(state: ResearchState) -> ResearchState:
    if state.skipped:
        pipeline_jobs_total.labels(stage="research", status="cache_hit").inc()
        return state
    if state.error:
        pipeline_jobs_total.labels(stage="research", status="failed").inc()
        return state

    bound = log.bind(company=state.company_name, node="persist_summary")
    posting_uuid = uuid.UUID(state.job_posting_id)
    raw_combined = f"{state.website_content}\n\n{state.job_page_content}".strip()

    async with async_session_factory() as session:
        summary = await company_summary_repository.upsert(
            session,
            job_posting_id=posting_uuid,
            company_name=state.company_name,
            raw_scraped_content=raw_combined or None,
            mission=state.mission or None,
            values=state.values or None,
            culture=state.culture or None,
            tech_stack=state.tech_stack or None,
            team_size_approx=state.team_size_approx or None,
            recent_news=state.recent_news or None,
            ai_summary=state.ai_summary or None,
        )
        await session.commit()
        summary_id = str(summary.id)

    pipeline_jobs_total.labels(stage="research", status="success").inc()
    bound.info("research.persisted", summary_id=summary_id)
    return state.model_copy(update={"summary_id": summary_id})


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _route_after_cache(state: ResearchState) -> str:
    if state.error:
        return "end"
    if state.skipped:
        return "end"
    return "scrape"


def _route_after_scrape(state: ResearchState) -> str:
    return "end" if state.error else "brief"


def build_research_graph() -> Any:
    graph = StateGraph(ResearchState)
    graph.add_node("check_cache", check_cache_node)
    graph.add_node("scrape", scrape_node)
    graph.add_node("generate_brief", generate_brief_node)
    graph.add_node("persist", persist_summary_node)
    graph.set_entry_point("check_cache")
    graph.add_conditional_edges(
        "check_cache",
        _route_after_cache,
        {"scrape": "scrape", "end": END},
    )
    graph.add_conditional_edges(
        "scrape",
        _route_after_scrape,
        {"brief": "generate_brief", "end": END},
    )
    graph.add_edge("generate_brief", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


_graph: Any | None = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_research_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def _trace_research_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {"job_posting_id": str(inputs.get("job_posting_id"))}


def _trace_research_outputs(output: Any) -> dict[str, Any]:
    state = output if isinstance(output, ResearchState) else None
    if state is None:
        return {"output_type": type(output).__name__}
    return {
        "summary_id": state.summary_id,
        "skipped": state.skipped,
        "has_error": state.error is not None,
    }


@traceable(
    run_type="chain",
    name="agent.research.run",
    tags=["agent", "research"],
    process_inputs=_trace_research_inputs,
    process_outputs=_trace_research_outputs,
)
async def run_research_agent(job_posting_id: str) -> ResearchState:
    """Run the research graph for one ``GOOD_FIT`` posting."""
    initial = ResearchState(job_posting_id=job_posting_id)
    started = time.perf_counter()
    try:
        result = await _get_graph().ainvoke(initial)
    finally:
        agent_duration_seconds.labels(agent_name=AGENT_NAME).observe(
            time.perf_counter() - started
        )
    if isinstance(result, ResearchState):
        return result
    return ResearchState.model_validate(result)


__all__ = [
    "AGENT_NAME",
    "BRIEF_INPUT_MAX_CHARS",
    "SCRAPE_MAX_CHARS",
    "FirecrawlClient",
    "ResearchState",
    "build_research_graph",
    "get_firecrawl_client",
    "get_llm",
    "run_research_agent",
    "set_firecrawl_client_for_tests",
    "set_llm_for_tests",
]
