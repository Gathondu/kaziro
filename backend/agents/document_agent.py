"""Document Agent — tailored CV + cover letter generator.

Triggered after the Research Agent completes for ``GOOD_FIT`` jobs in the
scheduled pipeline; ``MAYBE`` evaluations reach this agent only via explicit
user actions (e.g. job UI backfill / ``run_research_then_document``).
Given a ``job_evaluations`` row + the user's profile/CV, it:

1. Loads context (evaluation, posting, company brief, profile, master
   CV text — pulled from Storage if not cached on the profile row).
2. Tailors the CV to the role (no fabrication).
3. Writes a personalised cover letter that references the company.
4. Runs an LLM-based quality check (non-blocking).
5. Renders both docs to PDF, uploads to Storage, and persists or updates the
   ``application_docs`` row (same ``id`` when regenerating).

Tests inject fakes via ``set_llm_for_tests`` and ``set_pdf_renderer_for_tests``.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Final, Literal, Protocol, cast

from langgraph.graph import END, StateGraph
from langsmith import traceable
from pydantic import BaseModel, ConfigDict, Field

from backend.config import get_settings
from backend.db.repositories import (
    application_doc_repository,
    company_summary_repository,
    evaluation_repository,
    job_posting_repository,
    profile_repository,
)
from backend.db.session import async_session_factory
from backend.llm.openrouter import build_chat_model
from backend.logging_config import get_logger
from backend.metrics import (
    agent_duration_seconds,
    external_api_calls_total,
    pipeline_jobs_total,
)
from backend.services import pdf_renderer as default_pdf_renderer
from backend.services import storage as storage_service

log = get_logger(__name__)

AGENT_NAME: Final[str] = "document"
RAW_CV_TEXT_TRUNCATE: Final[int] = 6000
JOB_DESCRIPTION_TRUNCATE: Final[int] = 3000
QUALITY_CHECK_CV_TRUNCATE: Final[int] = 3000


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class DocumentState(BaseModel):
    """LangGraph state for the Document Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_evaluation_id: str
    user_id: str

    job_posting_id: str = ""
    job_title: str = ""
    job_description: str = ""
    job_requirements: list[str] = Field(default_factory=list)
    company_name: str = ""
    company_mission: str = ""
    company_values: str = ""
    company_culture: str = ""
    company_summary: str = ""

    user_full_name: str = ""
    user_skills: list[str] = Field(default_factory=list)
    user_experience_years: int | None = None
    user_summary: str = ""
    user_values: str = ""
    raw_cv_text: str = ""

    tailored_cv_text: str = ""
    cover_letter_text: str = ""
    # When set, skip one branch and refresh only that side (requires existing application_docs).
    regenerate_scope: Literal["cv", "cover_letter"] | None = None

    quality_passed: bool = False
    quality_notes: str = ""

    cv_pdf_path: str = ""
    cover_letter_pdf_path: str = ""

    application_doc_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Pluggable LLM + PDF renderer
# ---------------------------------------------------------------------------


class _Invokable(Protocol):
    async def ainvoke(self, prompt: str) -> Any: ...


class PdfRendererProtocol(Protocol):
    async def render_pdf_and_upload(
        self, content: str, *, title: str, storage_path: str
    ) -> str: ...

    def storage_path_for_doc(
        self, *, user_id: str | uuid.UUID, doc_kind: str, doc_id: str | uuid.UUID
    ) -> str: ...


class _PdfRendererAdapter:
    """Adapt the function-based ``pdf_renderer`` module to a protocol."""

    async def render_pdf_and_upload(self, content: str, *, title: str, storage_path: str) -> str:
        return await default_pdf_renderer.render_pdf_and_upload(
            content, title=title, storage_path=storage_path
        )

    def storage_path_for_doc(
        self, *, user_id: str | uuid.UUID, doc_kind: str, doc_id: str | uuid.UUID
    ) -> str:
        return default_pdf_renderer.storage_path_for_doc(
            user_id=user_id, doc_kind=doc_kind, doc_id=doc_id
        )


_llm: _Invokable | None = None
_pdf_renderer: PdfRendererProtocol | None = None


def _build_default_llm() -> _Invokable:
    settings = get_settings()
    return cast(
        _Invokable,
        build_chat_model(
            model=settings.LLM_MODEL_DOCUMENT,
            temperature=0.4,
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


def get_pdf_renderer() -> PdfRendererProtocol:
    global _pdf_renderer
    if _pdf_renderer is None:
        _pdf_renderer = _PdfRendererAdapter()
    return _pdf_renderer


def set_pdf_renderer_for_tests(renderer: PdfRendererProtocol | None) -> None:
    global _pdf_renderer
    _pdf_renderer = renderer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _invoke_text(prompt: str) -> str:
    try:
        response = await get_llm().ainvoke(prompt)
        external_api_calls_total.labels(service="openrouter", status="200").inc()
    except Exception:
        external_api_calls_total.labels(service="openrouter", status="error").inc()
        raise
    raw = getattr(response, "content", response)
    return raw.strip() if isinstance(raw, str) else str(raw).strip()


def _strip_json_fence(raw: str) -> str:
    body = raw.strip()
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


async def load_context_node(state: DocumentState) -> DocumentState:
    bound = log.bind(job_evaluation_id=state.job_evaluation_id, node="load_context")
    bound.info("document.load_start")

    user_uuid = uuid.UUID(state.user_id)
    eval_uuid = uuid.UUID(state.job_evaluation_id)
    saved_doc = None

    async with async_session_factory() as session:
        evaluation = await evaluation_repository.get_by_id(session, user_uuid, eval_uuid)
        if evaluation is None:
            bound.error("document.evaluation_not_found")
            return state.model_copy(update={"error": "Evaluation not found"})

        job = await job_posting_repository.get_by_id(session, evaluation.job_posting_id)
        profile = await profile_repository.get_by_user_id(session, user_uuid)
        if job is None or profile is None:
            bound.error(
                "document.context_load_failed",
                job_found=bool(job),
                profile_found=bool(profile),
            )
            return state.model_copy(update={"error": "Job or profile not found"})

        company = await company_summary_repository.get_for_posting(
            session, evaluation.job_posting_id
        )
        if state.regenerate_scope in ("cv", "cover_letter"):
            saved_doc = await application_doc_repository.get_by_evaluation_id(
                session, user_uuid, eval_uuid
            )

    raw_cv = profile.master_cv_text or ""
    if not raw_cv and profile.cv_storage_path:
        try:
            raw_cv = await storage_service.download_text(profile.cv_storage_path)
        except Exception as exc:
            bound.warning("document.cv_load_failed", error=str(exc))
            raw_cv = ""

    updates: dict[str, Any] = {
        "job_posting_id": str(job.id),
        "job_title": job.title,
        "job_description": (job.description or "")[:JOB_DESCRIPTION_TRUNCATE],
        "job_requirements": list(job.requirements or []),
        "company_name": job.company_name,
        "company_mission": (company.mission if company else "") or "",
        "company_values": (company.values if company else "") or "",
        "company_culture": (company.culture if company else "") or "",
        "company_summary": (company.ai_summary if company else "") or "",
        "user_full_name": profile.full_name,
        "user_skills": list(profile.skills or []),
        "user_experience_years": profile.experience_years,
        "user_summary": profile.professional_summary or "",
        "user_values": profile.values_statement or "",
        "raw_cv_text": raw_cv[:RAW_CV_TEXT_TRUNCATE],
    }
    if state.regenerate_scope == "cover_letter":
        if saved_doc is None:
            bound.error("document.regenerate_missing_row", scope="cover_letter")
            return state.model_copy(update={**updates, "error": "No saved documents to regenerate"})
        updates["tailored_cv_text"] = saved_doc.tailored_cv_text
    elif state.regenerate_scope == "cv":
        if saved_doc is None:
            bound.error("document.regenerate_missing_row", scope="cv")
            return state.model_copy(update={**updates, "error": "No saved documents to regenerate"})
        updates["cover_letter_text"] = saved_doc.cover_letter_text

    return state.model_copy(update=updates)


async def cv_tailor_node(state: DocumentState) -> DocumentState:
    bound = log.bind(job_title=state.job_title, node="cv_tailor")
    bound.info("document.cv_tailor_start")

    requirements_str = "\n".join(f"- {r}" for r in state.job_requirements[:20])
    cv_source = state.raw_cv_text or (
        f"No CV uploaded. User skills: {', '.join(state.user_skills)}.\n"
        f"Summary: {state.user_summary}"
    )

    prompt = f"""You are an expert resume writer helping a candidate tailor their CV for a specific role.

IMPORTANT RULES:
1. DO NOT fabricate experience, skills, or achievements that are not in the original CV.
2. DO reorder sections and bullet points to prioritise the most relevant experience FIRST.
3. DO rewrite bullet points to use stronger action verbs and highlight relevant outcomes.
4. DO naturally incorporate keywords from the job requirements where truthfully applicable.
5. Keep the same factual information — only improve presentation and relevance ordering.
6. Use clean, professional formatting with clear sections.

TARGET ROLE: {state.job_title} at {state.company_name}

KEY REQUIREMENTS:
{requirements_str}

ORIGINAL CV:
{cv_source}

Write a complete, tailored CV in clean plain text format. Use clear section headers
(EXPERIENCE, SKILLS, EDUCATION, etc.). Do NOT use markdown bold/italic — plain text only."""

    try:
        tailored = await _invoke_text(prompt)
    except Exception as exc:
        bound.error("document.cv_tailor_failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})

    bound.info("document.cv_tailored", chars=len(tailored))
    return state.model_copy(update={"tailored_cv_text": tailored})


async def cover_letter_node(state: DocumentState) -> DocumentState:
    bound = log.bind(job_title=state.job_title, node="cover_letter")
    bound.info("document.cover_letter_start")

    requirements_str = "\n".join(f"- {r}" for r in state.job_requirements[:10])

    prompt = f"""You are an expert cover letter writer. Write a compelling, personalised cover letter.

CANDIDATE: {state.user_full_name}
ROLE: {state.job_title}
COMPANY: {state.company_name}

COMPANY CONTEXT:
- Mission: {state.company_mission}
- Values: {state.company_values}
- Culture: {state.company_culture}
- About: {state.company_summary}

CANDIDATE PROFILE:
- Skills: {", ".join(state.user_skills)}
- Experience: {state.user_experience_years or "not specified"} years
- Summary: {state.user_summary}
- Personal Values: {state.user_values}

JOB REQUIREMENTS (address 2-3 of the most relevant):
{requirements_str}

GUIDELINES:
1. Opening: Hook with genuine enthusiasm — reference something specific about the company.
2. Body (2 paragraphs): Demonstrate relevant experience; connect candidate values to company values.
3. Closing: Clear call to action. Professional sign-off.
4. Tone: Professional but human. Not generic. Not sycophantic.
5. Length: 3-4 paragraphs, ~300-350 words.
6. Plain text format, no markdown.

Write the full cover letter now:"""

    try:
        cover_letter = await _invoke_text(prompt)
    except Exception as exc:
        bound.error("document.cover_letter_failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})

    bound.info("document.cover_letter_generated", chars=len(cover_letter))
    return state.model_copy(update={"cover_letter_text": cover_letter})


async def quality_check_node(state: DocumentState) -> DocumentState:
    bound = log.bind(job_title=state.job_title, node="quality_check")
    bound.info("document.quality_check_start")

    prompt = f"""Review these two job application documents for quality and consistency.

CHECK FOR:
1. Does the CV contain any claims that appear fabricated or inconsistent with the user profile?
2. Does the cover letter reference the correct company ({state.company_name}) and role ({state.job_title})?
3. Is the tone professional and appropriate throughout?
4. Are there any factual contradictions between the CV and cover letter?
5. Are there any obvious errors, placeholders, or template artifacts?

USER SKILLS (ground truth): {", ".join(state.user_skills)}

CV:
{state.tailored_cv_text[:QUALITY_CHECK_CV_TRUNCATE]}

COVER LETTER:
{state.cover_letter_text}

Respond in this exact JSON format (no other text):
{{
  "passed": true,
  "issues": [],
  "summary": "<1-2 sentence quality summary>"
}}"""

    try:
        raw = await _invoke_text(prompt)
        data = json.loads(_strip_json_fence(raw))
        passed = bool(data.get("passed", True))
        issues = data.get("issues") or []
        notes = str(data.get("summary", ""))
        if issues:
            notes = f"{notes} Issues: " + "; ".join(str(i) for i in issues)
        bound.info("document.quality_check_complete", passed=passed)
        return state.model_copy(update={"quality_passed": passed, "quality_notes": notes})
    except Exception as exc:
        bound.warning("document.quality_check_failed", error=str(exc))
        # Non-fatal — default to passed but record the failure.
        return state.model_copy(
            update={
                "quality_passed": True,
                "quality_notes": f"Quality check error: {exc}",
            }
        )


async def render_and_persist_node(state: DocumentState) -> DocumentState:
    bound = log.bind(job_evaluation_id=state.job_evaluation_id, node="render_persist")
    if state.error:
        pipeline_jobs_total.labels(stage="document", status="failed").inc()
        return state

    user_uuid = uuid.UUID(state.user_id)
    eval_uuid = uuid.UUID(state.job_evaluation_id)
    settings = get_settings()
    renderer = get_pdf_renderer()
    scope = state.regenerate_scope
    prev_cv_pdf = None
    prev_cl_pdf = None

    async with async_session_factory() as session:
        existing = await application_doc_repository.get_by_evaluation_id(
            session, user_uuid, eval_uuid
        )
        if existing is not None:
            prev_cv_pdf = existing.cv_pdf_path
            prev_cl_pdf = existing.cover_letter_pdf_path
            if scope == "cv":
                await application_doc_repository.update(
                    session,
                    user_uuid,
                    existing.id,
                    tailored_cv_text=state.tailored_cv_text,
                    cover_letter_text=state.cover_letter_text,
                    generation_model=settings.LLM_MODEL_DOCUMENT,
                    quality_passed=state.quality_passed,
                    quality_notes=state.quality_notes or None,
                    cv_pdf_path=None,
                    cover_letter_pdf_path=prev_cl_pdf,
                )
            elif scope == "cover_letter":
                await application_doc_repository.update(
                    session,
                    user_uuid,
                    existing.id,
                    tailored_cv_text=state.tailored_cv_text,
                    cover_letter_text=state.cover_letter_text,
                    generation_model=settings.LLM_MODEL_DOCUMENT,
                    quality_passed=state.quality_passed,
                    quality_notes=state.quality_notes or None,
                    cv_pdf_path=prev_cv_pdf,
                    cover_letter_pdf_path=None,
                )
            else:
                await application_doc_repository.update(
                    session,
                    user_uuid,
                    existing.id,
                    tailored_cv_text=state.tailored_cv_text,
                    cover_letter_text=state.cover_letter_text,
                    generation_model=settings.LLM_MODEL_DOCUMENT,
                    quality_passed=state.quality_passed,
                    quality_notes=state.quality_notes or None,
                    cv_pdf_path=None,
                    cover_letter_pdf_path=None,
                )
            await session.commit()
            doc_id = existing.id
            bound.info(
                "document.persist_update",
                application_doc_id=str(doc_id),
                regenerate_scope=scope or "full",
            )
        else:
            if scope is not None:
                pipeline_jobs_total.labels(stage="document", status="failed").inc()
                return state.model_copy(
                    update={
                        "error": "Cannot partial-regenerate without a saved document",
                    }
                )
            doc = await application_doc_repository.create(
                session,
                user_id=user_uuid,
                job_evaluation_id=eval_uuid,
                tailored_cv_text=state.tailored_cv_text,
                cover_letter_text=state.cover_letter_text,
                generation_model=settings.LLM_MODEL_DOCUMENT,
                quality_passed=state.quality_passed,
                quality_notes=state.quality_notes or None,
            )
            await session.commit()
            doc_id = doc.id
            bound.info("document.persist_create", application_doc_id=str(doc_id))

    cv_path = renderer.storage_path_for_doc(user_id=user_uuid, doc_kind="cv", doc_id=doc_id)
    cl_path = renderer.storage_path_for_doc(
        user_id=user_uuid, doc_kind="cover_letter", doc_id=doc_id
    )

    cv_uploaded = ""
    cl_uploaded = ""
    try:
        if scope == "cv":
            cv_uploaded = await renderer.render_pdf_and_upload(
                state.tailored_cv_text,
                title=f"CV — {state.user_full_name} — {state.job_title}",
                storage_path=cv_path,
            )
        elif scope == "cover_letter":
            cl_uploaded = await renderer.render_pdf_and_upload(
                state.cover_letter_text,
                title=f"Cover Letter — {state.company_name}",
                storage_path=cl_path,
            )
        else:
            cv_uploaded = await renderer.render_pdf_and_upload(
                state.tailored_cv_text,
                title=f"CV — {state.user_full_name} — {state.job_title}",
                storage_path=cv_path,
            )
            cl_uploaded = await renderer.render_pdf_and_upload(
                state.cover_letter_text,
                title=f"Cover Letter — {state.company_name}",
                storage_path=cl_path,
            )
    except Exception as exc:
        bound.warning("document.pdf_render_failed", error=str(exc))

    if scope == "cv" and cv_uploaded:
        async with async_session_factory() as session:
            await application_doc_repository.update(
                session,
                user_uuid,
                doc_id,
                cv_pdf_path=cv_uploaded,
            )
            await session.commit()
    elif scope == "cover_letter" and cl_uploaded:
        async with async_session_factory() as session:
            await application_doc_repository.update(
                session,
                user_uuid,
                doc_id,
                cover_letter_pdf_path=cl_uploaded,
            )
            await session.commit()
    elif scope is None and cv_uploaded and cl_uploaded:
        async with async_session_factory() as session:
            await application_doc_repository.attach_pdfs(
                session,
                user_uuid,
                doc_id,
                cv_pdf_path=cv_uploaded,
                cover_letter_pdf_path=cl_uploaded,
            )
            await session.commit()

    out_cv = cv_uploaded or (prev_cv_pdf or "")
    out_cl = cl_uploaded or (prev_cl_pdf or "")
    pipeline_jobs_total.labels(stage="document", status="success").inc()
    bound.info(
        "document.persisted",
        application_doc_id=str(doc_id),
        cv_path=out_cv,
        cover_letter_path=out_cl,
        regenerate_scope=scope or "full",
    )
    return state.model_copy(
        update={
            "application_doc_id": str(doc_id),
            "cv_pdf_path": out_cv,
            "cover_letter_pdf_path": out_cl,
        }
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _route_after_load(state: DocumentState) -> str:
    if state.error:
        return "error_end"
    if state.regenerate_scope == "cover_letter":
        return "cover_letter"
    return "cv_tailor"


def _route_after_cv(state: DocumentState) -> str:
    if state.error:
        return "error_end"
    if state.regenerate_scope == "cv":
        return "quality_check"
    return "cover_letter"


def _route_after_cl(state: DocumentState) -> str:
    return "error_end" if state.error else "quality_check"


async def _error_end_node(state: DocumentState) -> DocumentState:
    return state


def build_document_graph() -> Any:
    graph = StateGraph(DocumentState)
    graph.add_node("load_context", load_context_node)
    graph.add_node("cv_tailor", cv_tailor_node)
    graph.add_node("cover_letter", cover_letter_node)
    graph.add_node("quality_check", quality_check_node)
    graph.add_node("render_persist", render_and_persist_node)
    graph.add_node("error_end", _error_end_node)

    graph.set_entry_point("load_context")
    graph.add_conditional_edges(
        "load_context",
        _route_after_load,
        {
            "cv_tailor": "cv_tailor",
            "cover_letter": "cover_letter",
            "error_end": END,
        },
    )
    graph.add_conditional_edges(
        "cv_tailor",
        _route_after_cv,
        {
            "cover_letter": "cover_letter",
            "quality_check": "quality_check",
            "error_end": END,
        },
    )
    graph.add_conditional_edges(
        "cover_letter",
        _route_after_cl,
        {"quality_check": "quality_check", "error_end": END},
    )
    graph.add_edge("quality_check", "render_persist")
    graph.add_edge("render_persist", END)
    return graph.compile()


_graph: Any | None = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_document_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def _trace_document_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_evaluation_id": str(inputs.get("job_evaluation_id")),
        "user_id": str(inputs.get("user_id")),
        "regenerate_scope": inputs.get("regenerate_scope"),
    }


def _trace_document_outputs(output: Any) -> dict[str, Any]:
    state = output if isinstance(output, DocumentState) else None
    if state is None:
        return {"output_type": type(output).__name__}
    return {
        "application_doc_id": state.application_doc_id,
        "quality_passed": state.quality_passed,
        "has_error": state.error is not None,
    }


@traceable(
    run_type="chain",
    name="agent.document.run",
    tags=["agent", "document"],
    process_inputs=_trace_document_inputs,
    process_outputs=_trace_document_outputs,
)
async def run_document_agent(
    job_evaluation_id: str,
    user_id: str,
    *,
    regenerate_scope: Literal["cv", "cover_letter"] | None = None,
) -> DocumentState:
    """Run the document graph for one ``job_evaluations`` row."""
    initial = DocumentState(
        job_evaluation_id=job_evaluation_id,
        user_id=user_id,
        regenerate_scope=regenerate_scope,
    )
    started = time.perf_counter()
    try:
        result = await _get_graph().ainvoke(initial)
    finally:
        agent_duration_seconds.labels(agent_name=AGENT_NAME).observe(time.perf_counter() - started)
    if isinstance(result, DocumentState):
        return result
    return DocumentState.model_validate(result)


__all__ = [
    "AGENT_NAME",
    "DocumentState",
    "PdfRendererProtocol",
    "build_document_graph",
    "get_llm",
    "get_pdf_renderer",
    "run_document_agent",
    "set_llm_for_tests",
    "set_pdf_renderer_for_tests",
]
