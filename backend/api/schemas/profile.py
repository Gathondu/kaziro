"""``user_profiles`` request / response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field

from backend.api.schemas.common import ORMModel


class ProfileResponse(ORMModel):
    """Public projection of a :class:`UserProfile` row.

    Internal fields (``profile_embedding``, ``master_cv_text``,
    ``cv_storage_path``) are intentionally excluded — embeddings have no
    use on the wire, and storage paths are surfaced via signed URLs from
    the upload endpoint.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    professional_summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    domain: str | None = None
    values_statement: str | None = None
    linkedin_url: str | None = None
    has_master_cv: bool = Field(
        description="True when an uploaded CV has been parsed for this profile.",
    )
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """PATCH-style update body — every field optional."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    professional_summary: str | None = Field(default=None, max_length=4000)
    skills: list[str] | None = Field(
        default=None,
        max_length=200,
        description="Replace the full skills list (no merge semantics).",
    )
    experience_years: int | None = Field(default=None, ge=0, le=80)
    domain: str | None = Field(default=None, max_length=100)
    values_statement: str | None = Field(default=None, max_length=2000)
    linkedin_url: AnyHttpUrl | None = None


def to_response(profile: object) -> ProfileResponse:
    """Adapter so the route stays one expression long."""
    has_master_cv = bool(getattr(profile, "master_cv_text", None))
    return ProfileResponse.model_validate(
        {
            "id": profile.id,
            "user_id": profile.user_id,
            "full_name": profile.full_name,
            "professional_summary": profile.professional_summary,
            "skills": profile.skills or [],
            "experience_years": profile.experience_years,
            "domain": profile.domain,
            "values_statement": profile.values_statement,
            "linkedin_url": profile.linkedin_url,
            "has_master_cv": has_master_cv,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
    )


__all__ = ["ProfileResponse", "ProfileUpdateRequest", "to_response"]
