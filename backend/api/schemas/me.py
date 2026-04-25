"""``/me`` response schema."""

from __future__ import annotations

from pydantic import BaseModel


class MeResponse(BaseModel):
    """Minimal authenticated identity — used to verify app-side account status."""

    user_id: str


__all__ = ["MeResponse"]
