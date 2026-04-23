"""Shared FastAPI dependencies.

Centralised so routers don't reach into the DB / auth layers directly.
Use the ``*Dep`` aliases in route signatures — they're intentionally
short so that handlers stay readable.

Currently exposed:

* :data:`SessionDep` — yields an :class:`AsyncSession`.
* :data:`CurrentUser` — authenticated :class:`backend.db.models.user.User`.
* :data:`AdminUser` — authenticated user with the admin role.
* :data:`CurrentClaims` — verified JWT claims (no DB hit).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.user import User
from backend.db.session import get_session
from backend.services.auth import (
    AuthClaims,
    get_current_claims,
    get_current_user,
    require_admin,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
CurrentClaims = Annotated[AuthClaims, Depends(get_current_claims)]


__all__ = [
    "AdminUser",
    "CurrentClaims",
    "CurrentUser",
    "SessionDep",
]
