from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import Router

from apps.accounts import services
from apps.accounts.auth import jwt_auth
from apps.accounts.models import User
from apps.accounts.schemas import (
    ConfirmationResponse,
    ConfirmEmailPayload,
    ForgotPasswordPayload,
    LoginPayload,
    MeResponse,
    MessageResponse,
    RefreshPayload,
    ResendConfirmationPayload,
    ResendConfirmationResponse,
    ResetPasswordPayload,
    SignupPayload,
    SignupResponse,
    TokenData,
)
from apps.core.schemas import Envelope, envelope

auth_router = Router(tags=["auth"])


@auth_router.post(
    "/signup",
    response=Envelope[SignupResponse],
    url_name="auth_signup",
)
async def signup(request: HttpRequest, payload: SignupPayload) -> dict[str, object]:
    return envelope(await _signup(payload))


@auth_router.post("/login", response=Envelope[TokenData])
async def login(request: HttpRequest, payload: LoginPayload) -> dict[str, object]:
    token = await services.login(
        identifier=payload.identifier,
        password=payload.password.get_secret_value(),
    )
    return envelope(token)


@auth_router.post("/refresh", response=Envelope[TokenData])
async def refresh(request: HttpRequest, payload: RefreshPayload) -> dict[str, object]:
    return envelope(await services.refresh(payload.refresh_token))


@auth_router.post("/confirm-email", response=Envelope[ConfirmationResponse])
async def confirm_email(request: HttpRequest, payload: ConfirmEmailPayload) -> dict[str, object]:
    return envelope(await services.confirm_email(payload.token))


@auth_router.get("/confirm-email", response=Envelope[ConfirmationResponse])
async def confirm_email_get(request: HttpRequest, token: str) -> dict[str, object]:
    return envelope(await services.confirm_email(token))


@auth_router.post("/resend-confirmation", response=Envelope[ResendConfirmationResponse])
async def resend_confirmation(
    request: HttpRequest,
    payload: ResendConfirmationPayload,
) -> dict[str, object]:
    sent = await services.resend_confirmation(payload.email)
    return envelope(ResendConfirmationResponse(confirmation_sent=sent))


@auth_router.post("/forgot-password", response=Envelope[MessageResponse])
async def forgot_password(
    request: HttpRequest,
    payload: ForgotPasswordPayload,
) -> dict[str, object]:
    await services.request_password_reset(payload.email)
    return envelope(
        MessageResponse(message="If that account exists, a password reset link has been sent.")
    )


@auth_router.post("/reset-password", response=Envelope[MessageResponse])
async def reset_password(
    request: HttpRequest,
    payload: ResetPasswordPayload,
) -> dict[str, object]:
    await services.reset_password(payload.token, payload.new_password.get_secret_value())
    return envelope(MessageResponse(message="Password reset completed."))


@auth_router.get("/me", auth=jwt_auth, response=Envelope[MeResponse])
async def me(request: HttpRequest) -> dict[str, object]:
    return envelope(data=await services.me(cast(User, request.auth)))  # type: ignore


async def _signup(payload: SignupPayload) -> SignupResponse:
    return await services.signup(
        email=payload.email,
        password=payload.password.get_secret_value(),
        username=payload.username,
    )


__all__ = ["auth_router"]
