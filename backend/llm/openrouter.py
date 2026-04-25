"""LangChain OpenRouter chat models + OpenAI-compatible embeddings on OpenRouter."""

from __future__ import annotations

from typing import Any

from langchain_openai import OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter

from backend.config import Settings, get_settings
from backend.db.models import EMBEDDING_DIM

# OpenRouter exposes an OpenAI-compatible HTTP API (chat + embeddings).
OPENROUTER_OPENAI_COMPAT_BASE: str = "https://openrouter.ai/api/v1"


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
        "dimensions": EMBEDDING_DIM,
    }
    return OpenAIEmbeddings(**kwargs)
