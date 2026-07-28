"""Application document agent.

LangGraph loads a GOOD_FIT evaluation and source-grounded company summary,
generates tailored text with OpenRouter, renders PDFs, and persists Django data.
"""

from __future__ import annotations

import asyncio
import io
import json
import uuid
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from apps.documents.models import ApplicationDoc
from apps.jobs.models import CompanySummary, EvaluationClassification, JobEvaluation
from apps.pipeline.llm import OpenRouterClient
from apps.profiles.models import UserProfile
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()
document_llm = OpenRouterClient(settings.LLM_MODEL_DOCUMENT, temperature=0.4)


class DocumentState(BaseModel):
    evaluation_id: str
    user_id: str
    regenerate_scope: str = "all"
    context: dict[str, Any] = Field(default_factory=dict)
    tailored_cv_text: str = ""
    cover_letter_text: str = ""
    quality_passed: bool = False
    quality_notes: str = ""
    document_id: str | None = None
    error: str | None = None


async def load_data_node(state: DocumentState) -> DocumentState:
    log = logger.bind(
        user_id=state.user_id,
        job_evaluation_id=state.evaluation_id,
        agent_name="document",
        node="load_data",
    )
    log.info("document.load.start")
    try:
        evaluation = await JobEvaluation.objects.select_related("job_posting").aget(
            id=state.evaluation_id,
            user_id=state.user_id,
            final_classification=EvaluationClassification.GOOD_FIT,
        )
        profile = await UserProfile.objects.aget(user_id=state.user_id)
        summary = await CompanySummary.objects.aget(
            job_posting=evaluation.job_posting,
            failure_metadata={},
        )
        existing = await ApplicationDoc.objects.filter(job_evaluation=evaluation).afirst()
        context = {
            "profile": {
                "full_name": profile.full_name,
                "professional_summary": profile.professional_summary,
                "skills": profile.skills,
                "experience_years": profile.experience_years,
                "domain": profile.domain,
                "values_statement": profile.values_statement,
                "master_cv_text": profile.master_cv_text[:18_000],
            },
            "job": {
                "title": evaluation.job_posting.title,
                "company_name": evaluation.job_posting.company_name,
                "description": evaluation.job_posting.description[:14_000],
                "requirements": evaluation.job_posting.requirements,
            },
            "evaluation": {
                "scores": evaluation.dimension_scores,
                "feedback": evaluation.final_feedback,
            },
            "company": {
                "mission": summary.mission,
                "values": summary.values,
                "culture": summary.culture,
                "tech_stack": summary.tech_stack,
                "summary": summary.ai_summary,
                "citations": summary.field_citations,
            },
            "existing": {
                "tailored_cv_text": existing.tailored_cv_text if existing else "",
                "cover_letter_text": existing.cover_letter_text if existing else "",
            },
        }
        log.info("document.load.complete")
        return state.model_copy(update={"context": context})
    except Exception as exc:
        log.error("document.load.failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})


async def generate_node(state: DocumentState) -> DocumentState:
    log = logger.bind(
        user_id=state.user_id,
        job_evaluation_id=state.evaluation_id,
        agent_name="document",
        node="generate",
    )
    log.info("document.generate.start")
    try:
        prompt = f"""TASK
Generate truthful, tailored application documents for this candidate and job.

IMPORTANT RULES
- Never invent experience, skills, employers, dates, qualifications, or company facts.
- Use company facts only from the supplied research object.
- Preserve factual master-CV content.
- Scope is {state.regenerate_scope}; retain existing text for an unrequested side.

Respond in this exact JSON format:
{{
  "tailored_cv_text": "plain text CV",
  "cover_letter_text": "plain text cover letter",
  "quality_passed": true,
  "quality_notes": "brief checks performed"
}}

CONTEXT:
{json.dumps(state.context, default=str)[:45_000]}
"""
        response = await document_llm.json(prompt)
        existing = state.context.get("existing", {})
        tailored_cv = str(
            existing.get("tailored_cv_text")
            if state.regenerate_scope == "cover_letter"
            else response.get("tailored_cv_text") or ""
        )
        cover_letter = str(
            existing.get("cover_letter_text")
            if state.regenerate_scope == "cv"
            else response.get("cover_letter_text") or ""
        )
        if not tailored_cv or not cover_letter:
            raise ValueError("Document generation returned incomplete text")
        log.info("document.generate.complete")
        return state.model_copy(
            update={
                "tailored_cv_text": tailored_cv,
                "cover_letter_text": cover_letter,
                "quality_passed": bool(response.get("quality_passed", False)),
                "quality_notes": str(response.get("quality_notes") or ""),
            }
        )
    except Exception as exc:
        log.error("document.generate.failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})


async def persist_node(state: DocumentState) -> DocumentState:
    log = logger.bind(
        user_id=state.user_id,
        job_evaluation_id=state.evaluation_id,
        agent_name="document",
        node="persist",
    )
    log.info("document.persist.start")
    try:
        cv_pdf, cover_pdf = await asyncio.gather(
            asyncio.to_thread(_render_pdf, "Tailored CV", state.tailored_cv_text),
            asyncio.to_thread(_render_pdf, "Cover Letter", state.cover_letter_text),
        )
        base = f"applications/{state.user_id}/{state.evaluation_id}"
        cv_path = await asyncio.to_thread(
            _replace_storage_file,
            f"{base}/cv.pdf",
            cv_pdf,
        )
        cover_path = await asyncio.to_thread(
            _replace_storage_file,
            f"{base}/cover-letter.pdf",
            cover_pdf,
        )
        document, _ = await ApplicationDoc.objects.aupdate_or_create(
            job_evaluation_id=uuid.UUID(state.evaluation_id),
            defaults={
                "user_id": state.user_id,
                "tailored_cv_text": state.tailored_cv_text,
                "cover_letter_text": state.cover_letter_text,
                "cv_pdf_path": cv_path,
                "cover_letter_pdf_path": cover_path,
                "generation_model": settings.LLM_MODEL_DOCUMENT,
                "quality_passed": state.quality_passed,
                "quality_notes": state.quality_notes,
            },
        )
        log.info("document.persist.complete", document_id=str(document.id))
        return state.model_copy(update={"document_id": str(document.id)})
    except Exception as exc:
        log.error("document.persist.failed", error=str(exc))
        return state.model_copy(update={"error": str(exc)})


async def error_end_node(state: DocumentState) -> DocumentState:
    log = logger.bind(
        user_id=state.user_id,
        job_evaluation_id=state.evaluation_id,
        agent_name="document",
        node="error_end",
    )
    log.info("document.error_end.complete", error=state.error)
    return state


def route_after_load(state: DocumentState) -> str:
    return "error_end" if state.error else "generate"


def route_after_generate(state: DocumentState) -> str:
    return "error_end" if state.error else "persist"


def build_document_graph() -> Any:
    graph = StateGraph(DocumentState)
    graph.add_node("load_data", load_data_node)
    graph.add_node("generate", generate_node)
    graph.add_node("persist", persist_node)
    graph.add_node("error_end", error_end_node)
    graph.set_entry_point("load_data")
    graph.add_conditional_edges(
        "load_data", route_after_load, {"generate": "generate", "error_end": "error_end"}
    )
    graph.add_conditional_edges(
        "generate", route_after_generate, {"persist": "persist", "error_end": "error_end"}
    )
    graph.add_edge("persist", END)
    graph.add_edge("error_end", END)
    return graph.compile()


document_graph = build_document_graph()


async def run_document_agent(
    evaluation_id: str,
    user_id: str,
    regenerate_scope: str = "all",
) -> DocumentState:
    result = await document_graph.ainvoke(
        DocumentState(
            evaluation_id=evaluation_id,
            user_id=user_id,
            regenerate_scope=regenerate_scope,
        )
    )
    return result if isinstance(result, DocumentState) else DocumentState.model_validate(result)


def _render_pdf(title: str, text: str) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list[Any] = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for paragraph in text.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph.replace("&", "&amp;"), styles["BodyText"]))
            story.append(Spacer(1, 6))
    document.build(story)
    return buffer.getvalue()


def _replace_storage_file(path: str, payload: bytes) -> str:
    if default_storage.exists(path):
        default_storage.delete(path)
    return default_storage.save(path, ContentFile(payload))


__all__ = [
    "DocumentState",
    "build_document_graph",
    "document_graph",
    "run_document_agent",
]
