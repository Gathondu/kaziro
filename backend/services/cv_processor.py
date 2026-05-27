"""CV upload pipeline (PDF → text → storage → embedding).

The HTTP layer streams the upload into bytes and hands them off to
:func:`process_cv_upload`. The service:

1. Validates the file is a PDF (magic + size).
2. Extracts plain text with :mod:`pypdf`.
3. Uploads the original PDF to Supabase Storage at the user's
   canonical path (``users/<uid>/cv/master.pdf``).
4. Embeds the extracted text and patches ``user_profiles`` with the
   storage path, raw text, and a pgvector-compatible embedding.

Heavy work (PDF parse, embedding HTTP call, Supabase upload) runs in
the default threadpool so the FastAPI worker stays responsive.
"""

from __future__ import annotations

import asyncio
import io
import re
import uuid
from dataclasses import dataclass
from typing import Final, Protocol

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.exceptions import ApiError
from backend.db.models import EMBEDDING_DIM
from backend.db.repositories import profile_repository
from backend.logging_config import get_logger
from backend.services import storage as storage_service

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Limits / constants
# ---------------------------------------------------------------------------

MAX_PDF_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB
MIN_EXTRACTED_CHARS: Final[int] = 50  # guard against blank scans
PDF_MAGIC: Final[bytes] = b"%PDF-"

# Browsers may send ``application/octet-stream`` for file inputs; anything
# else that is not a wildcard/binary hint is rejected with 415.
_ALLOWED_CV_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "application/pdf",
        "application/octet-stream",
        "binary/octet-stream",
    }
)


def storage_path_for_user(user_id: uuid.UUID) -> str:
    """Canonical storage path for a user's master CV."""
    return f"users/{user_id}/cv/master.pdf"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CvUploadError(ApiError):
    status_code = 422
    code = "cv_upload_invalid"


# ---------------------------------------------------------------------------
# Embedder injection (mirrors parser_agent test hooks)
# ---------------------------------------------------------------------------


class _Embeddable(Protocol):
    async def aembed_query(self, text: str) -> list[float]: ...


_embedder: _Embeddable | None = None


def get_embedder() -> _Embeddable:
    """Reuse the parser agent's embedder so we share one embedding client."""
    global _embedder
    if _embedder is None:
        from backend.agents.parser_agent import (
            get_embedder as _get_parser_embedder,
        )

        _embedder = _get_parser_embedder()
    return _embedder


def set_embedder_for_tests(embedder: _Embeddable | None) -> None:
    global _embedder
    _embedder = embedder


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProcessedCv:
    storage_path: str
    text_chars: int
    embedding_dims: int
    signed_url: str


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def process_cv_upload(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    payload: bytes,
) -> ProcessedCv:
    """Validate → extract → store → embed → persist.

    The caller is responsible for committing the surrounding session.
    Raises :class:`CvUploadError` for any user-actionable failure
    (wrong type, oversize, unreadable PDF, blank text).
    """
    bound = log.bind(user_id=str(user_id), filename=filename)
    _validate_payload(payload, content_type)

    text = await asyncio.to_thread(_extract_text, payload)
    text = _normalise(text)
    if len(text) < MIN_EXTRACTED_CHARS:
        bound.warning("cv.extraction_insufficient", chars=len(text))
        raise CvUploadError(
            "Could not extract text from this PDF — try exporting it from "
            "Word/Google Docs rather than scanning a paper copy.",
            code="cv_text_extraction_failed",
        )
    profile = await profile_repository.get_by_user_id(session, user_id)
    if profile is None:
        raise CvUploadError(
            "Create your profile (PUT /profile) before uploading a CV.",
            code="profile_required",
        )

    path = storage_path_for_user(user_id)
    await storage_service.upload_bytes(
        path,
        payload,
        content_type="application/pdf",
        upsert=True,
    )

    try:
        embedding = await get_embedder().aembed_query(text)
        if len(embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"embedding dimension mismatch: got {len(embedding)}, expected {EMBEDDING_DIM}"
            )
    except Exception:
        bound.exception("cv.embedding_failed")
        raise CvUploadError(
            "Embedding service is currently unavailable — please retry shortly.",
            code="cv_embedding_failed",
            status_code=503,
        ) from None

    await profile_repository.update_master_cv(
        session,
        user_id,
        storage_path=path,
        extracted_text=text,
    )
    await profile_repository.update_embedding(session, user_id, embedding=embedding)

    signed_url = await storage_service.create_signed_url(path)

    bound.info(
        "cv.processed",
        chars=len(text),
        embedding_dims=len(embedding),
        storage_path=path,
    )
    return ProcessedCv(
        storage_path=path,
        text_chars=len(text),
        embedding_dims=len(embedding),
        signed_url=signed_url,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_payload(payload: bytes, content_type: str | None) -> None:
    if not payload:
        raise CvUploadError("Uploaded file is empty.", code="cv_empty")
    if len(payload) > MAX_PDF_BYTES:
        raise CvUploadError(
            f"PDF must be ≤ {MAX_PDF_BYTES // (1024 * 1024)} MB.",
            code="cv_too_large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    if content_type:
        base = content_type.split(";", 1)[0].strip().lower()
        if base not in _ALLOWED_CV_CONTENT_TYPES:
            raise CvUploadError(
                "Only PDF uploads are supported (Content-Type: application/pdf).",
                code="cv_unsupported_media_type",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
    if not payload.startswith(PDF_MAGIC):
        raise CvUploadError(
            "File is not a valid PDF (missing PDF header).",
            code="cv_not_pdf",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


def _extract_text(payload: bytes) -> str:
    """Run pypdf in the calling thread (already off-loop via to_thread)."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(payload), strict=False)
    except (PdfReadError, ValueError) as exc:
        raise CvUploadError(
            f"PDF appears corrupted: {exc}",
            code="cv_pdf_corrupt",
        ) from exc

    if reader.is_encrypted:
        # Try empty password (common for "view-only" PDFs).
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on file
            raise CvUploadError(
                "Encrypted PDFs are not supported — remove the password before uploading.",
                code="cv_pdf_encrypted",
            ) from exc

    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # pragma: no cover
            log.exception("cv.page_extract_failed")
    return "\n\n".join(pages)


_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


__all__ = [
    "MAX_PDF_BYTES",
    "MIN_EXTRACTED_CHARS",
    "CvUploadError",
    "ProcessedCv",
    "get_embedder",
    "process_cv_upload",
    "set_embedder_for_tests",
    "storage_path_for_user",
]
