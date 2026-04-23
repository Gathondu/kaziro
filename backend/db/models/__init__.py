"""ORM models package.

Importing this package side-effect-registers every model on
:data:`backend.db.base.Base.metadata` so Alembic autogenerate sees the
full schema. Always import via ``from backend.db.models import ...`` —
never reach into the per-table modules from outside ``backend/db/``.
"""

from __future__ import annotations

from backend.db.models.application import Application
from backend.db.models.application_doc import ApplicationDoc
from backend.db.models.application_event import ApplicationEvent
from backend.db.models.company_summary import (
    RAW_SCRAPED_CONTENT_MAX_BYTES,
    CompanySummary,
)
from backend.db.models.enums import (
    ApplicationDocType,
    ApplicationEventType,
    ApplicationStatus,
    Classification,
    JobSource,
    ParseStatus,
    SubscriptionTier,
)
from backend.db.models.job_evaluation import JobEvaluation
from backend.db.models.job_posting import EMBEDDING_DIM, JobPosting
from backend.db.models.job_search_config import JobSearchConfig
from backend.db.models.raw_job import RawJob
from backend.db.models.user import User
from backend.db.models.user_profile import UserProfile

__all__ = [
    "EMBEDDING_DIM",
    "RAW_SCRAPED_CONTENT_MAX_BYTES",
    "Application",
    "ApplicationDoc",
    "ApplicationDocType",
    "ApplicationEvent",
    "ApplicationEventType",
    "ApplicationStatus",
    "Classification",
    "CompanySummary",
    "JobEvaluation",
    "JobPosting",
    "JobSearchConfig",
    "JobSource",
    "ParseStatus",
    "RawJob",
    "SubscriptionTier",
    "User",
    "UserProfile",
]
