"""``GET /profile/cv.pdf`` — signed master CV download URL."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.db.models.enums import SubscriptionTier
from backend.db.models.user import User
from backend.db.session import get_session
from backend.main import create_app
from backend.services.auth import get_current_user


@pytest.fixture()
def authenticated_client() -> Generator[TestClient, None, None]:
    app = create_app()

    async def _fake_user() -> User:
        return User(
            id=uuid.UUID("00000000-0000-4000-8000-000000000101"),
            email="profile-cv-test@example.invalid",
            is_active=True,
            subscription_tier=SubscriptionTier.FREE,
        )

    async def _fake_session() -> AsyncGenerator[MagicMock, None]:
        yield MagicMock()

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_session] = _fake_session
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def test_profile_cv_download_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/profile/cv.pdf", follow_redirects=False)

    assert response.status_code == 401


def test_profile_cv_download_returns_404_when_profile_missing(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.api.routes.profile.profile_repository.get_by_user_id",
        AsyncMock(return_value=None),
    )

    response = authenticated_client.get("/api/v1/profile/cv.pdf", follow_redirects=False)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "profile_not_found"


def test_profile_cv_download_returns_404_when_cv_missing(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.api.routes.profile.profile_repository.get_by_user_id",
        AsyncMock(return_value=SimpleNamespace(cv_storage_path=None)),
    )

    response = authenticated_client.get("/api/v1/profile/cv.pdf", follow_redirects=False)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "cv_not_found"


def test_profile_cv_download_redirects_to_signed_url(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign = AsyncMock(return_value="https://signed.example/master-cv.pdf")
    monkeypatch.setattr(
        "backend.api.routes.profile.profile_repository.get_by_user_id",
        AsyncMock(return_value=SimpleNamespace(cv_storage_path="users/u/cv/master.pdf")),
    )
    monkeypatch.setattr("backend.api.routes.profile.storage_service.create_signed_url", sign)

    response = authenticated_client.get("/api/v1/profile/cv.pdf", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://signed.example/master-cv.pdf"
    sign.assert_awaited_once_with("users/u/cv/master.pdf")


def test_profile_cv_url_returns_signed_url_json(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign = AsyncMock(return_value="https://signed.example/master-cv.pdf")
    monkeypatch.setattr(
        "backend.api.routes.profile.profile_repository.get_by_user_id",
        AsyncMock(return_value=SimpleNamespace(cv_storage_path="users/u/cv/master.pdf")),
    )
    monkeypatch.setattr("backend.api.routes.profile.storage_service.create_signed_url", sign)

    response = authenticated_client.get("/api/v1/profile/cv-url")

    assert response.status_code == 200
    assert response.json()["data"] == {"signed_url": "https://signed.example/master-cv.pdf"}
    sign.assert_awaited_once_with("users/u/cv/master.pdf")
