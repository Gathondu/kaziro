from __future__ import annotations

import asyncio
import io

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader

from apps.accounts.models import User
from apps.core.exceptions import BadRequestError, NotFoundError
from apps.pipeline.llm import OpenRouterClient
from apps.profiles import repositories
from apps.profiles.models import UserProfile
from apps.profiles.schemas import (
    CvDownloadResponse,
    CvUploadResponse,
    ProfilePayload,
    ProfileResponse,
)
from config.logging import get_logger
from config.settings import get_settings

log = get_logger(__name__)
settings = get_settings()
embedding_client = OpenRouterClient(settings.LLM_MODEL_PARSER)


async def get_profile(user: User) -> ProfileResponse:
    profile = await repositories.get_for_user(user)
    if profile is None:
        raise NotFoundError("Profile not found.", code="profile_not_found")
    return to_response(profile)


async def upsert_profile(user: User, payload: ProfilePayload) -> ProfileResponse:
    skills = _clean_skills(payload.skills)
    profile = await repositories.upsert_for_user(
        user,
        full_name=payload.full_name,
        professional_summary=payload.professional_summary or "",
        skills=skills,
        experience_years=payload.experience_years,
        domain=payload.domain or "",
        values_statement=payload.values_statement or "",
        linkedin_url=str(payload.linkedin_url) if payload.linkedin_url else "",
    )
    log.info("profile.upserted", user_id=str(user.id), profile_id=str(profile.id))
    return to_response(profile)


async def upload_cv(user: User, file: UploadedFile) -> CvUploadResponse:
    profile = await repositories.get_for_user(user)
    if profile is None:
        raise NotFoundError("Create your profile before uploading a CV.", code="profile_required")
    if not _is_pdf(file):
        raise BadRequestError("Upload a PDF file.", code="invalid_cv_type")
    if file.size and file.size > 10 * 1024 * 1024:
        raise BadRequestError("CV files must be 10 MB or smaller.", code="cv_too_large")

    storage_path = f"profiles/{user.id}/master-cv.pdf"
    payload = await asyncio.to_thread(file.read)
    text = await asyncio.to_thread(_extract_pdf_text, payload)
    if not text.strip():
        raise BadRequestError("The PDF contains no extractable text.", code="cv_text_missing")
    embedding = await embedding_client.embedding(text[:20_000], settings.LLM_EMBEDDING_MODEL)
    saved_path = await asyncio.to_thread(_replace_file, storage_path, payload)
    original_filename = _safe_original_filename(file.name)
    profile.cv_storage_path = saved_path
    profile.cv_original_filename = original_filename
    profile.master_cv_text = text
    profile.profile_embedding = embedding
    await profile.asave(
        update_fields=[
            "cv_storage_path",
            "cv_original_filename",
            "master_cv_text",
            "profile_embedding",
            "updated_at",
        ]
    )
    log.info("profile.cv_uploaded", user_id=str(user.id), profile_id=str(profile.id))
    return CvUploadResponse(
        storage_path=saved_path,
        original_filename=original_filename,
        text_chars=len(text),
        embedding_dims=len(embedding),
        signed_url=default_storage.url(saved_path),
        has_master_cv=True,
    )


async def get_cv_url(user: User) -> CvDownloadResponse:
    profile = await repositories.get_for_user(user)
    if profile is None or not profile.cv_storage_path:
        raise NotFoundError("CV not found.", code="cv_not_found")
    return CvDownloadResponse(signed_url=default_storage.url(profile.cv_storage_path))


async def get_cv_content(user: User) -> tuple[bytes, str]:
    profile = await repositories.get_for_user(user)
    if profile is None or not profile.cv_storage_path:
        raise NotFoundError("CV not found.", code="cv_not_found")
    exists = await asyncio.to_thread(default_storage.exists, profile.cv_storage_path)
    if not exists:
        raise NotFoundError("CV file not found.", code="cv_file_not_found")
    content = await asyncio.to_thread(_read_storage_file, profile.cv_storage_path)
    filename = (
        profile.cv_original_filename
        or _storage_filename(profile.cv_storage_path)
        or "master-cv.pdf"
    )
    return content, filename


async def disable_account(user: User) -> None:
    from apps.jobs.models import JobSearchConfig

    user.is_active = False
    await user.asave(update_fields=["is_active"])
    await JobSearchConfig.objects.filter(user=user).aupdate(is_active=False)
    log.info("profile.account_disabled", user_id=str(user.id))


def to_response(profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,  # type: ignore
        full_name=profile.full_name,
        professional_summary=profile.professional_summary or None,
        skills=profile.skills or [],
        experience_years=profile.experience_years,
        domain=profile.domain or None,
        values_statement=profile.values_statement or None,
        linkedin_url=profile.linkedin_url or None,
        has_master_cv=bool(profile.cv_storage_path),
        cv_original_filename=profile.cv_original_filename
        or _storage_filename(profile.cv_storage_path),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _clean_skills(skills: list[str]) -> list[str]:
    return [skill.strip() for skill in skills if skill.strip()]


def _safe_original_filename(filename: str | None) -> str:
    normalized = (filename or "").replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    return (normalized or "master-cv.pdf")[:255]


def _storage_filename(storage_path: str) -> str | None:
    if not storage_path:
        return None
    return storage_path.replace("\\", "/").rsplit("/", maxsplit=1)[-1]


def _is_pdf(file: UploadedFile) -> bool:
    return file.content_type == "application/pdf" or file.name.lower().endswith(".pdf")  # type: ignore


def _extract_pdf_text(payload: bytes) -> str:
    reader = PdfReader(io.BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _replace_file(path: str, payload: bytes) -> str:
    if default_storage.exists(path):
        default_storage.delete(path)
    return default_storage.save(path, ContentFile(payload))


def _read_storage_file(path: str) -> bytes:
    with default_storage.open(path, "rb") as stored_file:
        return stored_file.read()


__all__ = [
    "disable_account",
    "get_cv_content",
    "get_cv_url",
    "get_profile",
    "to_response",
    "upload_cv",
    "upsert_profile",
]
