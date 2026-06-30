from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import File, Router
from ninja.files import UploadedFile

from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.core.schemas import Envelope, envelope
from apps.profiles import services
from apps.profiles.schemas import CvUploadResponse, ProfilePayload, ProfileResponse

profile_router = Router(tags=["profile"])
cv_file: UploadedFile = File(...)  # type: ignore


@profile_router.get("", auth=jwt_auth, response=Envelope[ProfileResponse])
async def get_profile(request: HttpRequest) -> dict[str, object]:
    return envelope(await services.get_profile(cast(User, request.auth)))  # type: ignore


@profile_router.put("", auth=jwt_auth, response=Envelope[ProfileResponse])
async def upsert_profile(request: HttpRequest, payload: ProfilePayload) -> dict[str, object]:
    return envelope(await services.upsert_profile(cast(User, request.auth), payload))  # type: ignore


@profile_router.post("/cv", auth=jwt_auth, response=Envelope[CvUploadResponse])
async def upload_cv(request: HttpRequest, file: UploadedFile = cv_file) -> dict[str, object]:
    return envelope(await services.upload_cv(cast(User, request.auth), file))  # type: ignore


__all__ = ["profile_router"]
