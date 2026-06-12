from __future__ import annotations

import uuid
from datetime import datetime

from ninja import Schema
from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator


class SignupPayload(Schema):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    username: str = Field(min_length=1, max_length=255)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return " ".join(value.split())


class LoginPayload(Schema):
    identifier: EmailStr | str = Field(min_length=3, max_length=20)
    password: SecretStr = Field(min_length=1, max_length=128)


class RefreshPayload(Schema):
    refresh_token: str = Field(min_length=1)


class ResendConfirmationPayload(Schema):
    email: EmailStr


class ConfirmEmailPayload(Schema):
    token: str = Field(min_length=16)


class ChangePasswordPayload(Schema):
    current_password: SecretStr
    new_password: SecretStr = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_must_differ(self) -> ChangePasswordPayload:
        if self.current_password.get_secret_value() == self.new_password.get_secret_value():
            raise ValueError("New password must be different.")
        return self


class TokenData(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: uuid.UUID


class SignupResponse(Schema):
    user_id: uuid.UUID
    email: EmailStr
    confirmation_required: bool = True
    confirmation_sent: bool


class ConfirmationResponse(Schema):
    user_id: uuid.UUID
    email: EmailStr
    confirmed_at: datetime
    token: TokenData


class ResendConfirmationResponse(Schema):
    confirmation_sent: bool


class MeResponse(Schema):
    id: uuid.UUID
    email: EmailStr
    username: str
    subscription_tier: str
    email_confirmed_at: datetime | None


__all__ = [
    "ChangePasswordPayload",
    "ConfirmEmailPayload",
    "ConfirmationResponse",
    "LoginPayload",
    "MeResponse",
    "RefreshPayload",
    "ResendConfirmationPayload",
    "ResendConfirmationResponse",
    "SignupPayload",
    "SignupResponse",
    "TokenData",
]
