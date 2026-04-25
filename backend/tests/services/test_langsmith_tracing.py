"""Tests for :mod:`backend.services.langsmith_tracing`."""

from __future__ import annotations

import pytest
from backend.config import get_settings
from backend.services.langsmith_tracing import apply_langsmith_tracing_from_settings


def test_langsmith_skipped_when_tracing_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    get_settings.cache_clear()
    settings = get_settings()
    # Must not raise; configure is a no-op path
    apply_langsmith_tracing_from_settings(settings)


def test_langsmith_skipped_in_test_env_even_when_flag_on(
    monkeypatch: pytest.MonkeyPatch, mocker: pytest.MockerFixture
) -> None:
    configure = mocker.patch("backend.services.langsmith_tracing.configure")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test-key")
    get_settings.cache_clear()
    apply_langsmith_tracing_from_settings(get_settings())
    configure.assert_not_called()


def test_langsmith_configure_when_development_and_on(
    monkeypatch: pytest.MonkeyPatch, mocker: pytest.MockerFixture
) -> None:
    configure = mocker.patch("backend.services.langsmith_tracing.configure")
    client_cls = mocker.patch("backend.services.langsmith_tracing.Client")
    fake_client = mocker.Mock()
    client_cls.return_value = fake_client

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-dev-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "unit-test-proj")
    get_settings.cache_clear()
    settings = get_settings()

    apply_langsmith_tracing_from_settings(settings)

    client_cls.assert_called_once()
    _, client_kwargs = client_cls.call_args
    assert client_kwargs["api_key"] == "ls-dev-key"
    configure.assert_called_once_with(
        enabled=True, client=fake_client, project_name="unit-test-proj"
    )
