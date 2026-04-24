"""``GET /job-configs/schedule-presets``."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.db.models.enums import SubscriptionTier
from backend.db.models.user import User
from backend.main import create_app
from backend.services.auth import get_current_user
from backend.services.schedule_presets import FETCH_CRON_DAILY, FETCH_CRON_WEEKLY


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = create_app()

    async def _fake_user() -> User:
        return User(
            id=uuid.uuid4(),
            email="preset-test@example.invalid",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE,
        )

    app.dependency_overrides[get_current_user] = _fake_user
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_schedule_presets_returns_two_entries(client: TestClient) -> None:
    response = client.get("/api/v1/job-configs/schedule-presets")
    assert response.status_code == 200
    body = response.json()
    assert body.get("error") is None
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) == 2
    ids = {row["id"] for row in data}
    assert ids == {"daily", "weekly"}
    crons = {row["fetch_schedule_cron"] for row in data}
    assert crons == {FETCH_CRON_DAILY, FETCH_CRON_WEEKLY}
    for row in data:
        assert "label" in row and isinstance(row["label"], str)
