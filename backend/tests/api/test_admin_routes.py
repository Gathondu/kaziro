"""Admin route smoke checks (T3.7)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from backend.main import create_app

    return TestClient(create_app())


def test_admin_users_requires_auth(client: TestClient) -> None:
    r = client.get("/api/v1/admin/users")
    assert r.status_code == 401
