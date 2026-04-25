"""``/me`` — lightweight authenticated session check (Supabase JWT + app user active)."""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter

from backend.api.deps import CurrentUser
from backend.api.schemas.common import Envelope, envelope
from backend.api.schemas.me import MeResponse

router: Final[APIRouter] = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "",
    response_model=Envelope[MeResponse],
    summary="Current app user (fails with 403 if the account is deactivated)",
)
async def get_me(current_user: CurrentUser) -> Envelope[MeResponse]:
    return envelope(MeResponse(user_id=str(current_user.id)))


__all__ = ["router"]
