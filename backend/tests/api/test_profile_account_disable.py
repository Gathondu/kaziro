"""``POST /profile/account/disable`` — self-service account deactivation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings
from backend.main import create_app
from backend.services.auth import EXPECTED_AUDIENCE, SUPABASE_ALGORITHM


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_profile_account_disable_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/profile/account/disable")
    assert response.status_code == 401


@pytest.mark.integration
def test_profile_account_disable_sets_is_active_false() -> None:
    settings = get_settings()
    uid = uuid.uuid4()
    email = f"{uid.hex[:12]}@acct-disable.test"
    secret = settings.SUPABASE_JWT_SECRET.get_secret_value()
    token = jwt.encode(
        {
            "sub": str(uid),
            "email": email,
            "aud": EXPECTED_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            "role": "authenticated",
        },
        secret,
        algorithm=SUPABASE_ALGORITHM,
    )
    sync_url = str(settings.DATABASE_URL_SYNC)
    if sync_url.startswith("postgresql://") and "+psycopg" not in sync_url:
        sync_url = "postgresql+psycopg://" + sync_url.removeprefix("postgresql://")
    sync_eng = create_engine(sync_url, pool_pre_ping=True)
    inserted_row = False
    try:
        try:
            with sync_eng.connect() as ping:
                ping.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            pytest.skip(f"DB not available: {exc}")

        try:
            with sync_eng.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO users (id, email, is_active, subscription_tier, "
                        "created_at, updated_at) VALUES "
                        "(CAST(:id AS uuid), :email, true, 'FREE', NOW(), NOW())"
                    ),
                    {"id": str(uid), "email": email},
                )
        except SQLAlchemyError as exc:
            pytest.skip(f"DB not ready: {exc}")
        inserted_row = True

        app = create_app()
        with TestClient(app) as tc:
            response = tc.post(
                "/api/v1/profile/account/disable",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 204

        with sync_eng.connect() as conn:
            row = conn.execute(
                text("SELECT is_active FROM users WHERE id = CAST(:id AS uuid)"),
                {"id": str(uid)},
            ).mappings().one()
        assert row["is_active"] is False
    finally:
        if inserted_row:
            try:
                with sync_eng.begin() as conn:
                    conn.execute(
                        text("DELETE FROM users WHERE id = CAST(:id AS uuid)"),
                        {"id": str(uid)},
                    )
            except SQLAlchemyError:
                pass
        sync_eng.dispose()
