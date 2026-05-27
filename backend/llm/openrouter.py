"""LangChain OpenRouter chat models + OpenAI-compatible embeddings on OpenRouter."""

from __future__ import annotations

import json
from typing import Any

from langchain_openai import OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter

from backend.config import Settings, get_settings
from backend.db.models import EMBEDDING_DIM

# OpenRouter exposes an OpenAI-compatible HTTP API (chat + embeddings).
OPENROUTER_OPENAI_COMPAT_BASE: str = "https://openrouter.ai/api/v1"
OPENROUTER_RETRYABLE_PROVIDER_CODES: set[int] = {
    408,
    429,
    500,
    502,
    503,
    504,
    520,
    522,
    524,
}


def provider_error_code(exc: Exception) -> int | None:
    """Extract an OpenRouter provider error code from SDK exceptions.

    OpenRouter can return a provider error envelope in an HTTP 200 response.
    The SDK then raises a response-validation error while trying to parse the
    envelope as a chat completion, so normal HTTP-status retry logic misses it.
    """
    body = getattr(exc, "body", None)
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            error = parsed.get("error")
            if isinstance(error, dict):
                code = error.get("code")
                if isinstance(code, int):
                    return code

    text = str(exc).lower()
    for code in OPENROUTER_RETRYABLE_PROVIDER_CODES:
        if f'"code": {code}' in text or f'"code":{code}' in text or f"'code': {code}" in text:
            return code
    return None


def is_retryable_provider_error(exc: Exception) -> bool:
    """Return true for transient OpenRouter provider-error envelopes."""
    code = provider_error_code(exc)
    if code in OPENROUTER_RETRYABLE_PROVIDER_CODES:
        return True
    text = str(exc).lower()
    return "response validation failed" in text and "provider returned error" in text


def build_chat_model(
    *,
    model: str,
    temperature: float,
    settings: Settings | None = None,
) -> ChatOpenRouter:
    """Return a :class:`ChatOpenRouter` with shared timeout/retry/attribution."""
    s = settings or get_settings()
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "api_key": s.OPENROUTER_API_KEY.get_secret_value(),
        "max_retries": s.OPENROUTER_MAX_RETRIES,
        # OpenRouter SDK expects milliseconds (see ``ChatOpenRouter.request_timeout``).
        "timeout": s.OPENROUTER_TIMEOUT_SECONDS * 1000,
    }
    if s.OPENROUTER_API_BASE is not None:
        kwargs["base_url"] = str(s.OPENROUTER_API_BASE).rstrip("/")
    if s.OPENROUTER_APP_URL is not None:
        kwargs["app_url"] = str(s.OPENROUTER_APP_URL).rstrip("/")
    if s.OPENROUTER_APP_TITLE is not None:
        kwargs["app_title"] = s.OPENROUTER_APP_TITLE
    return ChatOpenRouter(**kwargs)


def build_embeddings(settings: Settings | None = None) -> OpenAIEmbeddings:
    """Embeddings via OpenRouter's OpenAI-compatible ``POST /v1/embeddings``."""
    s = settings or get_settings()
    if s.LLM_EMBEDDING_DIM != EMBEDDING_DIM:
        raise ValueError(
            "LLM_EMBEDDING_DIM must match pgvector EMBEDDING_DIM "
            f"({s.LLM_EMBEDDING_DIM} != {EMBEDDING_DIM})"
        )
    base = (
        str(s.OPENROUTER_API_BASE).rstrip("/")
        if s.OPENROUTER_API_BASE is not None
        else OPENROUTER_OPENAI_COMPAT_BASE
    )
    kwargs: dict[str, Any] = {
        "model": s.LLM_EMBEDDING_MODEL,
        "openai_api_key": s.OPENROUTER_API_KEY,
        "openai_api_base": base,
        "encoding_format": "float",
        "check_embedding_ctx_length": False,
        "dimensions": s.LLM_EMBEDDING_DIM,
    }
    return OpenAIEmbeddings(**kwargs)
