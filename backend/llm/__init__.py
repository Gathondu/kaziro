"""Shared LLM client factories."""

from backend.llm.openrouter import (
    OPENROUTER_OPENAI_COMPAT_BASE,
    build_chat_model,
    build_embeddings,
)

__all__ = [
    "OPENROUTER_OPENAI_COMPAT_BASE",
    "build_chat_model",
    "build_embeddings",
]
