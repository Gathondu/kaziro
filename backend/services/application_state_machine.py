"""Application status transitions as data (see application-state-machine diagram)."""

from __future__ import annotations

from backend.db.models.enums import ApplicationStatus

_ALLOWED: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.DRAFT: frozenset({ApplicationStatus.SENT, ApplicationStatus.WITHDRAWN}),
    ApplicationStatus.SENT: frozenset(
        {
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.INTERVIEWING: frozenset(
        {
            ApplicationStatus.OFFERED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.OFFERED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


def can_transition(current: ApplicationStatus, target: ApplicationStatus) -> bool:
    """Return True if ``current → target`` is allowed."""
    if current is target:
        return True
    return target in _ALLOWED.get(current, frozenset())


def allowed_targets(current: ApplicationStatus) -> frozenset[ApplicationStatus]:
    """Return the set of legal next statuses (excluding no-op)."""
    return _ALLOWED.get(current, frozenset())


__all__ = ["allowed_targets", "can_transition"]
