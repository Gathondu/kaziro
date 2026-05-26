"""Database enum types.

Each :class:`enum.StrEnum` here is registered with SQLAlchemy via
``SAEnum(..., name="<snake_case>_enum")`` and is **the** in-Python
representation of the corresponding Postgres enum. Never store the
string value directly — always import the enum and use a member.
"""

from __future__ import annotations

from enum import StrEnum


class SubscriptionTier(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class JobSource(StrEnum):
    """Upstream job-search provider."""

    RAPIDAPI = "rapidapi"
    MANUAL_URL = "manual_url"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"


class ParseStatus(StrEnum):
    PENDING = "PENDING"
    PARSED = "PARSED"
    FAILED = "FAILED"


class Classification(StrEnum):
    """Final evaluator decision for a (user, job) pair."""

    GOOD_FIT = "GOOD_FIT"
    MAYBE = "MAYBE"
    REJECT = "REJECT"


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    INTERVIEWING = "INTERVIEWING"
    OFFERED = "OFFERED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class ApplicationDocType(StrEnum):
    CV = "CV"
    COVER_LETTER = "COVER_LETTER"


class ApplicationEventType(StrEnum):
    CREATED = "CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NOTE_ADDED = "NOTE_ADDED"
    DOC_REGENERATED = "DOC_REGENERATED"


__all__ = [
    "ApplicationDocType",
    "ApplicationEventType",
    "ApplicationStatus",
    "Classification",
    "JobSource",
    "ParseStatus",
    "SubscriptionTier",
]
