"""Auth request / response schemas.

The bodies here mirror the relevant portions of the Supabase Auth
GoTrue API (https://supabase.com/docs/reference/api/auth) so that the
proxy layer can pass them through with minimal translation.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, SecretStr


class RegisterRequest(BaseModel):
    """Sign-up payload."""

    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="Optional display name; persisted in user_metadata.",
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Pared-down view of the Supabase token bundle.

    Only fields the frontend needs to drive the session; we deliberately
    avoid forwarding internal Supabase fields (``provider_token``, etc.)
    so callers don't grow accidental dependencies on them.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires.")
    user_id: str | None = Field(default=None, description="Supabase auth.users.id.")


class RegisterResponse(BaseModel):
    """Result of a registration attempt.

    Supabase may return a session immediately, *or* require email
    confirmation first — in which case ``token`` is null and the client
    should prompt the user to check their inbox.
    """

    user_id: str
    email: EmailStr
    confirmation_required: bool
    token: TokenResponse | None = None


__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "RegisterResponse",
    "TokenResponse",
]
