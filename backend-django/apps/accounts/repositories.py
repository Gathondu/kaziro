from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.accounts.models import User


def users() -> QuerySet[User]:
    return User.objects.all()


async def get_by_email(email: str) -> User | None:
    normalized = User.objects.normalize_email(email)
    return await users().filter(email__iexact=normalized).afirst()

async def get_by_identifier(identifier: str) -> User | None:
    return await users().filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).afirst()


async  def get_by_id(user_id: str) -> User | None:
    return await users().filter(id=user_id).afirst()


async def get_by_confirmation_hash(token_hash: str) -> User | None:
    return await users().filter(email_confirmation_token_hash=token_hash).afirst()


__all__ = ["get_by_confirmation_hash", "get_by_email", "get_by_id", "users"]
