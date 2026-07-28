from __future__ import annotations

import asyncio
import io
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from apps.documents.models import ApplicationDoc


async def update_document_content(
    document: ApplicationDoc,
    *,
    tailored_cv_text: str,
    cover_letter_text: str,
) -> ApplicationDoc:
    cv_pdf, cover_pdf = await asyncio.gather(
        asyncio.to_thread(render_pdf, "Tailored CV", tailored_cv_text),
        asyncio.to_thread(render_pdf, "Cover Letter", cover_letter_text),
    )
    # pyrefly: ignore [missing-attribute]
    base = f"applications/{document.user_id}/{document.job_evaluation_id}"
    document.cv_pdf_path = await asyncio.to_thread(
        replace_storage_file,
        f"{base}/cv.pdf",
        cv_pdf,
    )
    document.cover_letter_pdf_path = await asyncio.to_thread(
        replace_storage_file,
        f"{base}/cover-letter.pdf",
        cover_pdf,
    )
    document.tailored_cv_text = tailored_cv_text
    document.cover_letter_text = cover_letter_text
    document.last_edited_at = timezone.now()
    await document.asave()
    return document


def render_pdf(title: str, text: str) -> bytes:
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


def replace_storage_file(path: str, payload: bytes) -> str:
    if default_storage.exists(path):
        default_storage.delete(path)
    return default_storage.save(path, ContentFile(payload))


__all__ = ["render_pdf", "replace_storage_file", "update_document_content"]
