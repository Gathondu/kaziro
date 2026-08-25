from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.jobs.fetcher import build_request, validate_draft_with_smoke_request
from apps.jobs.models import JobSourceConfigDraft
from apps.jobs.source_config import validate_provider_config
from config.settings import get_configured_env


def provider_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "base_url": "https://jsearch.p.rapidapi.com",
        "endpoint_path": "/search",
        "auth": {
            "type": "static_header",
            "header_name": "X-RapidAPI-Key",
            "credential_env_var": "RAPIDAPI_KEY",
        },
    }
    config.update(overrides)
    return config


class JobSourceRequestHeaderTests(SimpleTestCase):
    def test_builds_rapidapi_key_and_config_defined_host_headers(self) -> None:
        config = validate_provider_config(
            provider_config(
                request_headers=[
                    {
                        "name": "X-RapidAPI-Host",
                        "value": "jsearch.p.rapidapi.com",
                    }
                ]
            )
        )

        with patch.dict("os.environ", {"RAPIDAPI_KEY": "test-secret"}):
            _, headers = build_request(config, None)

        assert headers["X-RapidAPI-Key"] == "test-secret"
        assert headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"

    def test_rapidapi_runtime_ignores_legacy_host_and_credential_env_names(
        self,
    ) -> None:
        config = validate_provider_config(
            provider_config(
                auth={
                    "type": "static_header",
                    "header_name": "X-RapidAPI-Key",
                    "credential_env_var": "LEGACY_API_KEY",
                },
                request_headers=[
                    {
                        "name": "X-RapidAPI-Host",
                        "value_env_var": "RAPIDAPI_HOST",
                    }
                ],
            )
        )

        with patch.dict(
            "os.environ",
            {
                "RAPIDAPI_KEY": "test-secret",
                "RAPIDAPI_HOST": "wrong.example.com",
            },
        ):
            _, headers = build_request(config, None)

        assert headers["X-RapidAPI-Key"] == "test-secret"
        assert headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"

    def test_supports_optional_environment_backed_additional_header(
        self,
    ) -> None:
        config = validate_provider_config(
            provider_config(
                request_headers=[
                    {
                        "name": "X-Partner-Token",
                        "value_env_var": "PARTNER_TOKEN",
                    }
                ]
            )
        )

        with patch.dict(
            "os.environ",
            {"RAPIDAPI_KEY": "test-secret", "PARTNER_TOKEN": "partner-secret"},
        ):
            _, headers = build_request(config, None)

        assert headers["X-Partner-Token"] == "partner-secret"

    def test_provider_credentials_fall_back_to_selected_dotenv_file(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("RAPIDAPI_KEY=dotenv-secret\n", encoding="utf-8")
            with (
                patch.dict("os.environ", {}, clear=True),
                patch("config.settings._ENV_FILE", str(env_file)),
            ):
                assert get_configured_env("RAPIDAPI_KEY") == "dotenv-secret"

    def test_process_environment_takes_precedence_over_dotenv_file(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("RAPIDAPI_KEY=dotenv-secret\n", encoding="utf-8")
            with (
                patch.dict(
                    "os.environ",
                    {"RAPIDAPI_KEY": "process-secret"},
                    clear=True,
                ),
                patch("config.settings._ENV_FILE", str(env_file)),
            ):
                assert get_configured_env("RAPIDAPI_KEY") == "process-secret"

    def test_rejects_literal_sensitive_header_values(self) -> None:
        with self.assertRaises(ValidationError):
            validate_provider_config(
                provider_config(
                    request_headers=[
                        {
                            "name": "X-RapidAPI-Key",
                            "value": "must-not-be-stored",
                        }
                    ]
                )
            )

    def test_rejects_authenticated_config_without_credential_environment_variable(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            validate_provider_config(
                provider_config(
                    auth={
                        "type": "static_header",
                        "header_name": "X-RapidAPI-Key",
                    }
                )
            )

    def test_rejects_header_newline_injection(self) -> None:
        with self.assertRaises(ValidationError):
            validate_provider_config(
                provider_config(
                    request_headers=[
                        {
                            "name": "X-RapidAPI-Host",
                            "value": "good.example\r\nInjected: yes",
                        }
                    ]
                )
            )

    def test_validation_uses_smoke_params_and_returns_full_diagnostics(
        self,
    ) -> None:
        draft = JobSourceConfigDraft(
            config=provider_config(
                request_headers=[
                    {
                        "name": "X-RapidAPI-Host",
                        "value": "jsearch.p.rapidapi.com",
                    }
                ],
                smoke_test_params={
                    "query": "software engineer in Nairobi",
                    "country": "ke",
                    "page": "1",
                },
            )
        )
        response_payload = {"status": "ERROR", "message": "Invalid parameter"}
        with (
            patch.dict("os.environ", {"RAPIDAPI_KEY": "test-secret"}),
            patch(
                "apps.jobs.fetcher._get_json",
                return_value=(
                    400,
                    response_payload,
                    {"Content-Type": "application/json"},
                ),
            ),
        ):
            result = async_to_sync(validate_draft_with_smoke_request)(draft)

        ok, request_url, request_headers, status, metadata, payload, errors = result
        assert not ok
        assert "query=software+engineer+in+Nairobi" in request_url
        assert "country=ke" in request_url
        assert "page=1" in request_url
        assert request_headers["X-RapidAPI-Key"] == "<redacted>"
        assert request_headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"
        assert status == 400
        assert metadata["response_headers"] == {"Content-Type": "application/json"}
        assert payload == response_payload
        assert errors == ["Provider returned HTTP 400."]

    def test_validation_reads_jobs_from_configured_nested_response_path(
        self,
    ) -> None:
        draft = JobSourceConfigDraft(
            config=provider_config(
                response_list_path="data.jobs",
                response_mapping={"external_id": "job_id"},
            )
        )
        response_payload = {"data": {"jobs": [{"job_id": "job-1"}], "cursor": "next"}}
        with (
            patch.dict("os.environ", {"RAPIDAPI_KEY": "test-secret"}),
            patch(
                "apps.jobs.fetcher._get_json",
                return_value=(
                    200,
                    response_payload,
                    {"Content-Type": "application/json"},
                ),
            ),
        ):
            result = async_to_sync(validate_draft_with_smoke_request)(draft)

        ok, _, _, status, metadata, payload, errors = result
        assert ok
        assert status == 200
        assert metadata["jobs_seen"] == 1
        assert payload == response_payload
        assert errors == []

    def test_validation_finds_common_nested_job_list_for_existing_drafts(
        self,
    ) -> None:
        draft = JobSourceConfigDraft(config=provider_config())
        response_payload = {"data": {"jobs": [{"job_id": "job-1"}]}}
        with (
            patch.dict("os.environ", {"RAPIDAPI_KEY": "test-secret"}),
            patch(
                "apps.jobs.fetcher._get_json",
                return_value=(200, response_payload, {}),
            ),
        ):
            result = async_to_sync(validate_draft_with_smoke_request)(draft)

        assert result[0]
        assert result[4]["jobs_seen"] == 1
