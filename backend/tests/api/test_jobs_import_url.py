"""``POST /jobs/import-url``."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.db.models.enums import SubscriptionTier
from backend.db.models.user import User
from backend.main import create_app
from backend.services.auth import get_current_user


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = create_app()

    async def _fake_user() -> User:
        return User(
            id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
            email="import-url-test@example.invalid",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE,
        )

    app.dependency_overrides[get_current_user] = _fake_user
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_import_url_queues_task(client: TestClient) -> None:
    with patch(
        "backend.services.jobs_service.trigger_job_url_import",
        new=AsyncMock(return_value=("task-1", False)),
    ) as trigger:
        response = client.post(
            "/api/v1/jobs/import-url",
            json={"url": "HTTPS://Jobs.Example.com/role?x=1#ignored"},
        )

    assert response.status_code == 202
    assert response.json()["data"] == {"task_id": "task-1", "duplicate": False}
    trigger.assert_awaited_once()
    assert trigger.await_args.args[1] == "https://jobs.example.com/role?x=1"
    assert trigger.await_args.kwargs["schedule_immediate"] is not None


def test_import_url_accepts_empty_company_url(client: TestClient) -> None:
    with patch(
        "backend.services.jobs_service.trigger_job_url_import",
        new=AsyncMock(return_value=("task-1", False)),
    ) as trigger:
        response = client.post(
            "/api/v1/jobs/import-url",
            json={"url": "https://jobs.example.com/role", "company_url": None},
        )

    assert response.status_code == 202
    assert response.json()["data"] == {"task_id": "task-1", "duplicate": False}
    trigger.assert_awaited_once()
    assert trigger.await_args.args[1] == "https://jobs.example.com/role"
    assert trigger.await_args.kwargs["company_url"] is None


def test_import_url_rejects_non_http_url(client: TestClient) -> None:
    response = client.post("/api/v1/jobs/import-url", json={"url": "ftp://example.com/job"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
