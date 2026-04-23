"""Illegal application status transitions must be rejected (T3.4)."""

from __future__ import annotations

import pytest

from backend.db.models.enums import ApplicationStatus
from backend.services.application_state_machine import can_transition


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [
        (ApplicationStatus.DRAFT, ApplicationStatus.SENT, True),
        (ApplicationStatus.DRAFT, ApplicationStatus.INTERVIEWING, False),
        (ApplicationStatus.SENT, ApplicationStatus.INTERVIEWING, True),
        (ApplicationStatus.SENT, ApplicationStatus.DRAFT, False),
        (ApplicationStatus.INTERVIEWING, ApplicationStatus.OFFERED, True),
        (ApplicationStatus.OFFERED, ApplicationStatus.SENT, False),
        (ApplicationStatus.REJECTED, ApplicationStatus.SENT, False),
        (ApplicationStatus.WITHDRAWN, ApplicationStatus.SENT, False),
    ],
)
def test_transition_matrix(
    current: ApplicationStatus, target: ApplicationStatus, expected: bool
) -> None:
    assert can_transition(current, target) is expected


def test_no_op_same_status_is_allowed() -> None:
    assert can_transition(ApplicationStatus.SENT, ApplicationStatus.SENT) is True
