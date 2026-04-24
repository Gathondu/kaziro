"""Versioned API router aggregator.

Mount every public ``/api/v1/*`` route here. Health, metrics, and
auth-proxy are exempt from the ``/api/v1``.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter

from backend.api.routes import admin as admin_routes
from backend.api.routes import applications as applications_routes
from backend.api.routes import auth as auth_routes
from backend.api.routes import job_configs as job_configs_routes
from backend.api.routes import jobs as jobs_routes
from backend.api.routes import profile as profile_routes
from backend.api.routes import ws as ws_routes

API_V1_PREFIX: Final[str] = "/api/v1"

api_v1_router: Final[APIRouter] = APIRouter(prefix=API_V1_PREFIX)
api_v1_router.include_router(profile_routes.router)
api_v1_router.include_router(job_configs_routes.router)
api_v1_router.include_router(jobs_routes.router)
api_v1_router.include_router(applications_routes.router)
api_v1_router.include_router(admin_routes.router)
api_v1_router.include_router(ws_routes.router)

# /auth/* routes live at the root for convenience (no JWT to validate
# the prefix against). Mounted on the bare app, not the v1 router.
auth_router: Final[APIRouter] = auth_routes.router


__all__ = ["API_V1_PREFIX", "api_v1_router", "auth_router"]
