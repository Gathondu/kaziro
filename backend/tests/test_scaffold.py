from __future__ import annotations

from django.test import Client, SimpleTestCase


class ScaffoldSmokeTests(SimpleTestCase):
    def test_health_envelope(self) -> None:
        response = Client().get("/health")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "ok"

    def test_api_meta_envelope(self) -> None:
        response = Client().get("/api/v1/meta")
        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["stack"] == "django-ninja"
        assert payload["error"] is None
