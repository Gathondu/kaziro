from __future__ import annotations

from django.test import SimpleTestCase

from apps.jobs.deduplication import normalize_job_url, stable_job_external_id


class JobDeduplicationTests(SimpleTestCase):
    def test_normalizes_tracking_parameters_and_fragments(self) -> None:
        first = normalize_job_url(
            "HTTPS://Jobs.Example.com/roles/123/?utm_source=search&job=123#apply"
        )
        second = normalize_job_url("https://jobs.example.com/roles/123?job=123")

        assert first == second

    def test_application_url_is_stable_when_provider_id_changes(self) -> None:
        url = "https://jobs.example.com/roles/123"

        assert stable_job_external_id(url, "provider-id-one") == stable_job_external_id(
            url,
            "provider-id-two",
        )

    def test_provider_id_is_used_when_application_url_is_missing(self) -> None:
        assert stable_job_external_id("", "provider-id") == "provider-id"
