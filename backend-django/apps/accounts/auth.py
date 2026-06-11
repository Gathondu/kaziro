"""Placeholder JWT auth for future Django-owned sessions."""

from __future__ import annotations

from typing import Any

from ninja.security import HttpBearer


class PlaceholderJWTAuth(HttpBearer):
    """Scaffold-only auth backend.

    Real token issuance and validation will be implemented in the auth
    migration slice. Returning ``None`` keeps protected routes inaccessible
    until that work is explicit.
    """

    def authenticate(self, request: Any, token: str) -> None:
        return None


jwt_auth = PlaceholderJWTAuth()

__all__ = ["jwt_auth", "PlaceholderJWTAuth"]
