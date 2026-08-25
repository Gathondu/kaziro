from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError

from apps.core.exceptions import UpstreamError
from apps.jobs.discovery_client import (
    DiscoveryResult,
    _normalize_discovery_response,
    _post_json_sync,
)
from apps.jobs.models import (
    DiscoveryRunStatus,
    DraftStatus,
    JobSourceConfigDraft,
    JobSourceDiscoveryRun,
    JobSourceProvider,
    ProviderStatus,
)
from apps.jobs.repositories import active_provider_drafts
from apps.jobs.tasks import _discover_provider
from asgiref.sync import async_to_sync
from django.test import SimpleTestCase, TransactionTestCase


class JobSourceDiscoveryClientTests(SimpleTestCase):
    def test_normalizes_nested_deployed_service_draft(self) -> None:
        response = {
            "draft": {
                "base_url": "https://api.example.com",
                "endpoint_path": "/jobs",
                "method": "GET",
                "query_params": {"keywords": "query"},
                "pagination": {"type": "page", "page_param": "page"},
                "auth": {
                    "type": "bearer",
                    "credential_env_var": "EXAMPLE_API_KEY",
                },
                "request_headers": [
                    {
                        "name": "X-RapidAPI-Host",
                        "value": "example.p.rapidapi.com",
                    }
                ],
                "smoke_test_params": {
                    "query": "software engineer",
                    "page": "1",
                },
                "response_mapping": {"external_id": "id"},
                "confidence_score": 0.7,
                "evidence_urls": ["https://example.com/docs"],
            },
            "confidence_score": 0.9,
            "evidence_urls": ["https://example.com/openapi.json"],
            "warnings": ["Review pagination."],
            "endpoint_candidates": [{"url": "https://api.example.com/jobs"}],
        }

        result = _normalize_discovery_response(response)

        assert result.config["base_url"] == "https://api.example.com/"
        assert result.config["endpoint_path"] == "/jobs"
        assert result.config["request_headers"] == [
            {
                "name": "X-RapidAPI-Host",
                "value": "example.p.rapidapi.com",
                "value_env_var": None,
            }
        ]
        assert result.config["smoke_test_params"] == {
            "query": "software engineer",
            "page": "1",
        }
        assert result.confidence_score == 0.9
        assert result.evidence_urls == ["https://example.com/openapi.json"]
        assert result.metadata["warnings"] == ["Review pagination."]

    def test_normalizes_current_discovery_contract(self) -> None:
        response = {
            "draft": {
                "base_url": "https://jsearch.p.rapidapi.com",
                "endpoint_path": "/search",
                "method": "GET",
                "query_params": {},
                "pagination": {"type": "none", "default_page_size": 10},
                "auth": {
                    "type": "static_header",
                    "header_name": "X-RapidAPI-Key",
                    "credential_env_var": "RAPIDAPI_KEY",
                },
                "request_headers": [
                    {
                        "name": "X-RapidAPI-Host",
                        "value": "jsearch.p.rapidapi.com",
                    }
                ],
                "smoke_test_params": {},
                "response_list_path": "data",
                "response_mapping": {},
                "examples": [],
                "confidence_score": 0.85,
                "evidence_urls": [],
            },
            "confidence_score": 0.85,
            "evidence_urls": [],
            "warnings": [],
        }

        result = _normalize_discovery_response(response)

        assert result.config["response_list_path"] == "data"
        assert result.config["examples"] == []
        assert result.evidence_urls == []
        assert result.confidence_score == 0.85

    def test_normalizes_discovered_rapidapi_host_and_credential_env(
        self,
    ) -> None:
        result = _normalize_discovery_response(
            {
                "draft": {
                    "base_url": "https://jsearch.p.rapidapi.com",
                    "endpoint_path": "/search",
                    "auth": {
                        "type": "static_header",
                        "header_name": "X-RapidAPI-Key",
                        "credential_env_var": "RAPIDAPI_HOST",
                    },
                    "request_headers": [
                        {
                            "name": "X-RapidAPI-Host",
                            "value_env_var": "RAPIDAPI_HOST",
                        }
                    ],
                },
                "host": "discovered-jsearch.p.rapidapi.com",
            }
        )

        # pyrefly: ignore [bad-index]
        assert result.config["auth"]["credential_env_var"] == "RAPIDAPI_KEY"
        assert result.config["request_headers"] == [
            {
                "name": "X-RapidAPI-Host",
                "value": "discovered-jsearch.p.rapidapi.com",
                "value_env_var": None,
            }
        ]

    def test_non_rapidapi_config_keeps_discovered_auth_env(self) -> None:
        result = _normalize_discovery_response(
            {
                "draft": {
                    "base_url": "https://api.example.com",
                    "endpoint_path": "/jobs",
                    "auth": {
                        "type": "bearer",
                        "credential_env_var": "EXAMPLE_API_TOKEN",
                    },
                }
            }
        )

        assert (
            # pyrefly: ignore [bad-index]
            result.config["auth"]["credential_env_var"]
            == "EXAMPLE_API_TOKEN"
        )

    def test_rejects_response_without_nested_draft(self) -> None:
        with self.assertRaises(UpstreamError):
            _normalize_discovery_response(
                {"base_url": "https://api.example.com"}
            )

    def test_rejects_invalid_nested_draft(self) -> None:
        with self.assertRaises(UpstreamError):
            _normalize_discovery_response(
                {"draft": {"endpoint_path": "/jobs"}}
            )

    def test_maps_timeout_to_safe_upstream_error(self) -> None:
        with (
            patch(
                "apps.jobs.discovery_client.urlopen", side_effect=TimeoutError
            ),
            self.assertRaises(UpstreamError),
        ):
            _post_json_sync("http://scrapper:3100/discover", {}, 1)

    def test_preserves_http_error_details(self) -> None:
        error = HTTPError(
            "http://scrapper:3100/discover",
            500,
            "Internal Server Error",
            # pyrefly: ignore [bad-argument-type]
            hdrs=None,
            fp=BytesIO(b'{"message":"crawler failed"}'),
        )
        with (
            patch("apps.jobs.discovery_client.urlopen", side_effect=error),
            self.assertRaisesRegex(
                UpstreamError,
                r"HTTP 500: \{\"message\":\"crawler failed\"\}",
            ),
        ):
            _post_json_sync("http://scrapper:3100/discover", {}, 1)


class JobSourceDiscoveryTaskTests(TransactionTestCase):
    def setUp(self) -> None:
        self.provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )
        self.discovery_run = JobSourceDiscoveryRun.objects.create(
            provider=self.provider
        )

    def test_successful_run_links_generated_draft_and_metadata(self) -> None:
        result = DiscoveryResult(
            config={
                "base_url": "https://api.example.com/",
                "endpoint_path": "/jobs",
                "method": "GET",
                "query_params": {},
                "pagination": {"type": "none", "default_page_size": 10},
                "auth": {"type": "none"},
                "response_mapping": {},
                "confidence_score": 0.8,
                "evidence_urls": ["https://example.com/docs"],
            },
            confidence_score=0.8,
            evidence_urls=["https://example.com/docs"],
            metadata={"warnings": []},
        )
        with patch(
            "apps.jobs.discovery_client.discover_provider_config",
            new=AsyncMock(return_value=result),
        ):
            draft_id = async_to_sync(_discover_provider)(
                str(self.provider.id), str(self.discovery_run.id), None, []
            )

        self.discovery_run.refresh_from_db()
        assert self.discovery_run.status == DiscoveryRunStatus.SUCCEEDED
        assert str(self.discovery_run.draft_id) == draft_id
        assert self.discovery_run.metadata == {"warnings": []}
        assert self.discovery_run.completed_at is not None

    def test_failed_run_records_sanitized_error(self) -> None:
        with (
            patch(
                "apps.jobs.discovery_client.discover_provider_config",
                new=AsyncMock(side_effect=RuntimeError("scraper unavailable")),
            ),
            self.assertRaises(RuntimeError),
        ):
            async_to_sync(_discover_provider)(
                str(self.provider.id), str(self.discovery_run.id), None, []
            )

        self.discovery_run.refresh_from_db()
        assert self.discovery_run.status == DiscoveryRunStatus.FAILED
        assert self.discovery_run.error_message == "scraper unavailable"
        assert self.discovery_run.completed_at is not None

    async def test_active_provider_drafts_selects_all_active_approved_providers(
        self,
    ) -> None:
        active_provider = await JobSourceProvider.objects.acreate(
            slug="active-jobs",
            display_name="Active Jobs",
            docs_url="https://active.example.com/docs",
            status=ProviderStatus.ACTIVE,
        )
        inactive_provider = await JobSourceProvider.objects.acreate(
            slug="inactive-jobs",
            display_name="Inactive Jobs",
            docs_url="https://inactive.example.com/docs",
            status=ProviderStatus.DISABLED,
        )
        unapproved_provider = await JobSourceProvider.objects.acreate(
            slug="unapproved-jobs",
            display_name="Unapproved Jobs",
            docs_url="https://unapproved.example.com/docs",
            status=ProviderStatus.ACTIVE,
        )
        config = {
            "base_url": "https://api.example.com",
            "endpoint_path": "/jobs",
            "auth": {"type": "none"},
        }
        await JobSourceConfigDraft.objects.acreate(
            provider=active_provider,
            config=config,
            status=DraftStatus.APPROVED,
        )
        await JobSourceConfigDraft.objects.acreate(
            provider=inactive_provider,
            config=config,
            status=DraftStatus.APPROVED,
        )
        await JobSourceConfigDraft.objects.acreate(
            provider=unapproved_provider,
            config=config,
            status=DraftStatus.VALIDATED,
        )

        drafts = await active_provider_drafts()

        assert [draft.provider.slug for draft in drafts] == ["active-jobs"]
