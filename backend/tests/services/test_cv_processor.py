"""CV upload service tests (mocked storage + embedder)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.services import cv_processor
from fastapi import status

from tests.support.pdf_minimal import pdf_bytes_with_text


@pytest.fixture
def _reset_cv_embedder() -> None:
    cv_processor.set_embedder_for_tests(None)
    yield
    cv_processor.set_embedder_for_tests(None)


@pytest.mark.asyncio
async def test_process_cv_upload_happy_path(
    monkeypatch: pytest.MonkeyPatch, _reset_cv_embedder: None
) -> None:
    uid = uuid.uuid4()
    body = "x" * 120
    pdf = pdf_bytes_with_text(body)

    monkeypatch.setattr(
        "backend.services.cv_processor.profile_repository",
        MagicMock(
            get_by_user_id=AsyncMock(
                return_value=MagicMock(id=uuid.uuid4(), user_id=uid)
            ),
            update_master_cv=AsyncMock(),
            update_embedding=AsyncMock(),
        ),
    )
    monkeypatch.setattr(
        "backend.services.cv_processor.storage_service",
        MagicMock(
            upload_bytes=AsyncMock(return_value="path"),
            create_signed_url=AsyncMock(return_value="https://signed.example/cv"),
        ),
    )

    class _Emb:
        async def aembed_query(self, text: str) -> list[float]:
            return [0.02] * 1536

    cv_processor.set_embedder_for_tests(_Emb())

    session = MagicMock()
    result = await cv_processor.process_cv_upload(
        session,
        user_id=uid,
        filename="cv.pdf",
        content_type="application/pdf",
        payload=pdf,
    )
    assert result.text_chars >= cv_processor.MIN_EXTRACTED_CHARS
    assert result.embedding_dims == 1536
    assert result.signed_url.startswith("https://")


@pytest.mark.asyncio
async def test_cv_upload_rejects_oversize(
    monkeypatch: pytest.MonkeyPatch, _reset_cv_embedder: None
) -> None:
    uid = uuid.uuid4()
    monkeypatch.setattr(
        "backend.services.cv_processor.profile_repository",
        MagicMock(get_by_user_id=AsyncMock(return_value=MagicMock())),
    )
    huge = b"%PDF-1.4" + b"0" * (cv_processor.MAX_PDF_BYTES + 1)
    session = MagicMock()
    with pytest.raises(cv_processor.CvUploadError) as ei:
        await cv_processor.process_cv_upload(
            session,
            user_id=uid,
            filename="big.pdf",
            content_type="application/pdf",
            payload=huge,
        )
    assert ei.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_cv_upload_rejects_non_pdf_content_type(
    monkeypatch: pytest.MonkeyPatch, _reset_cv_embedder: None
) -> None:
    uid = uuid.uuid4()
    monkeypatch.setattr(
        "backend.services.cv_processor.profile_repository",
        MagicMock(get_by_user_id=AsyncMock(return_value=MagicMock())),
    )
    pdf = pdf_bytes_with_text("hello " * 30)
    session = MagicMock()
    with pytest.raises(cv_processor.CvUploadError) as ei:
        await cv_processor.process_cv_upload(
            session,
            user_id=uid,
            filename="x.png",
            content_type="image/png",
            payload=pdf,
        )
    assert ei.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


@pytest.mark.asyncio
async def test_cv_upload_rejects_invalid_pdf_magic(
    monkeypatch: pytest.MonkeyPatch, _reset_cv_embedder: None
) -> None:
    uid = uuid.uuid4()
    monkeypatch.setattr(
        "backend.services.cv_processor.profile_repository",
        MagicMock(get_by_user_id=AsyncMock(return_value=MagicMock())),
    )
    session = MagicMock()
    with pytest.raises(cv_processor.CvUploadError) as ei:
        await cv_processor.process_cv_upload(
            session,
            user_id=uid,
            filename="x.pdf",
            content_type="application/pdf",
            payload=b"not a pdf",
        )
    assert ei.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
