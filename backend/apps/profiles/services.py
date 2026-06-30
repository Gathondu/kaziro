from __future__ import annotations

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile

from apps.accounts.models import User
from apps.core.exceptions import BadRequestError, NotFoundError
from apps.profiles import repositories
from apps.profiles.models import UserProfile
from apps.profiles.schemas import CvUploadResponse, ProfilePayload, ProfileResponse
from config.logging import get_logger

log = get_logger(__name__)


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

    storage_path = f"profiles/{user.id}/master-cv.pdf"
    if default_storage.exists(storage_path):
        default_storage.delete(storage_path)
    saved_path = default_storage.save(storage_path, file)
    profile.cv_storage_path = saved_path
    profile.master_cv_text = ""
    await profile.asave(update_fields=["cv_storage_path", "master_cv_text", "updated_at"])
    log.info("profile.cv_uploaded", user_id=str(user.id), profile_id=str(profile.id))
    return CvUploadResponse(storage_path=saved_path, text_chars=0, has_master_cv=True)


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
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _clean_skills(skills: list[str]) -> list[str]:
    return [skill.strip() for skill in skills if skill.strip()]


def _is_pdf(file: UploadedFile) -> bool:
    return file.content_type == "application/pdf" or file.name.lower().endswith(".pdf")  # type: ignore


__all__ = ["get_profile", "to_response", "upload_cv", "upsert_profile"]
