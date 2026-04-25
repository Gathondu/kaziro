"""``/profile`` routes — read, partial update, CV upload, and self-service disable."""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter, File, Response, UploadFile, status

from backend.api.deps import CurrentUser, SessionDep
from backend.api.exceptions import NotFoundError
from backend.api.schemas.common import Envelope, envelope
from backend.api.schemas.profile import (
    CvUploadResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    to_response,
)
from backend.db.repositories import profile_repository
from backend.logging_config import get_logger
from backend.services import cv_processor, user_lifecycle

log = get_logger(__name__)

router: Final[APIRouter] = APIRouter(prefix="/profile", tags=["profile"])


@router.get(
    "",
    response_model=Envelope[ProfileResponse],
    summary="Get the authenticated user's profile",
)
async def get_profile(session: SessionDep, current_user: CurrentUser) -> Envelope[ProfileResponse]:
    profile = await profile_repository.get_by_user_id(session, current_user.id)
    if profile is None:
        raise NotFoundError(
            "profile not found — call PUT /profile to create it",
            code="profile_not_found",
        )
    return envelope(to_response(profile))


@router.put(
    "",
    response_model=Envelope[ProfileResponse],
    summary="Create or partially update the authenticated user's profile",
)
async def upsert_profile(
    payload: ProfileUpdateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Envelope[ProfileResponse]:
    existing = await profile_repository.get_by_user_id(session, current_user.id)

    # PUT semantics for the *first* call: full_name is required when the
    # row doesn't exist yet; subsequent PUTs may omit it (PATCH-style).
    full_name = payload.full_name or (existing.full_name if existing else None)
    if full_name is None:
        raise NotFoundError(
            "full_name is required to create a profile",
            code="full_name_required",
        )

    update_fields = payload.model_dump(exclude_unset=True, exclude={"full_name"})
    if "linkedin_url" in update_fields and update_fields["linkedin_url"] is not None:
        update_fields["linkedin_url"] = str(update_fields["linkedin_url"])

    profile = await profile_repository.upsert(
        session,
        user_id=current_user.id,
        full_name=full_name,
        **update_fields,
    )
    await session.commit()
    return envelope(to_response(profile))


@router.post(
    "/cv",
    status_code=status.HTTP_201_CREATED,
    response_model=Envelope[CvUploadResponse],
    summary="Upload a master CV PDF (extracts text + recomputes embedding)",
)
async def upload_master_cv(
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="PDF up to 10 MB."),
) -> Envelope[CvUploadResponse]:
    """Validate, store, parse, and embed the user's master CV."""
    payload = await file.read()
    try:
        result = await cv_processor.process_cv_upload(
            session,
            user_id=current_user.id,
            filename=file.filename or "cv.pdf",
            content_type=file.content_type,
            payload=payload,
        )
    finally:
        await file.close()

    await session.commit()

    return envelope(
        CvUploadResponse(
            signed_url=result.signed_url,
            storage_path=result.storage_path,
            text_chars=result.text_chars,
            embedding_dims=result.embedding_dims,
        )
    )


@router.post(
    "/account/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Disable the authenticated user's account (cannot sign in to the app)",
)
async def disable_own_account(session: SessionDep, current_user: CurrentUser) -> Response:
    """Soft-deactivate the current user row. The client should sign out of Supabase."""
    log_bound = log.bind(user_id=str(current_user.id))
    log_bound.info("profile.account_disable.start")
    updated = await user_lifecycle.deactivate_user_and_job_schedules(
        session,
        current_user.id,
    )
    if updated is None:
        log_bound.warning("profile.account_disable.user_missing")
        raise NotFoundError("user not found", code="user_not_found")
    await session.commit()
    log_bound.info("profile.account_disable.complete")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
