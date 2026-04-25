"""OpenRouter-backed builder for host-routed RapidAPI providers."""

from __future__ import annotations

import json
from typing import Any, Final, Protocol, cast

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langsmith import traceable
from pydantic import BaseModel, Field

from backend.config import Settings, get_settings
from backend.llm.openrouter import build_chat_model
from backend.logging_config import get_logger
from backend.services.rapidapi_providers import jsearch, linkedin_fantastic
from backend.services.rapidapi_types import RapidApiQuerySpec

log = get_logger(__name__)


class _StructuredInvoker(Protocol):
    async def ainvoke(self, messages: list[Any]) -> Any: ...


class _ToolInvoker(Protocol):
    async def ainvoke(self, messages: list[Any]) -> Any: ...


class _ProviderModule(Protocol):
    PROVIDER_KEY: str
    SUPPORTED_HOSTS: frozenset[str]
    REFERENCE_PATH: Any

    def build_system_prompt(self) -> str: ...

    def validate_and_clamp_spec(
        self, spec: RapidApiQuerySpec, *, settings: Settings
    ) -> RapidApiQuerySpec: ...


_ALL_PROVIDERS: Final[tuple[_ProviderModule, ...]] = (
    cast(_ProviderModule, jsearch),
    cast(_ProviderModule, linkedin_fantastic),
)
_PROVIDER_BY_HOST: Final[dict[str, _ProviderModule]] = {
    host.lower(): provider for provider in _ALL_PROVIDERS for host in provider.SUPPORTED_HOSTS
}
_structured_by_provider: dict[str, _StructuredInvoker] = {}


class _BuildRapidApiUrlInput(BaseModel):
    path: str = Field(description="URL path segment only, no leading slash.")
    query_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific query parameters.",
    )


def _resolve_provider(settings: Settings) -> _ProviderModule:
    host = str(settings.RAPIDAPI_HOST).strip().lower()
    provider = _PROVIDER_BY_HOST.get(host)
    if provider is None:
        supported = ", ".join(sorted(_PROVIDER_BY_HOST))
        raise ValueError(f"unsupported RAPIDAPI_HOST {host!r}. Supported hosts: {supported}")
    return provider


def _default_structured_model(settings: Settings) -> _StructuredInvoker:
    base = build_chat_model(
        model=settings.LLM_MODEL_PARSER,
        temperature=0,
        settings=settings,
    )
    return cast(_StructuredInvoker, base.with_structured_output(RapidApiQuerySpec))


def _default_tool_model(settings: Settings) -> _ToolInvoker:
    base = build_chat_model(
        model=settings.LLM_MODEL_PARSER,
        temperature=0,
        settings=settings,
    )
    rapidapi_url_tool = _make_build_rapidapi_url_tool(settings)
    bound = cast(Any, base).bind_tools(
        [rapidapi_url_tool],
        tool_choice="build_rapidapi_url",
    )
    return cast(_ToolInvoker, bound)


def _make_build_rapidapi_url_tool(settings: Settings) -> BaseTool:
    @tool("build_rapidapi_url", args_schema=_BuildRapidApiUrlInput)
    def build_rapidapi_url(path: str, query_params: dict[str, Any]) -> dict[str, Any]:
        """Validate a query spec and build a full RapidAPI URL."""
        spec = RapidApiQuerySpec(path=path, query_params=query_params)
        url, pairs = build_get_url_and_params(spec, settings=settings)
        return {
            "url": url,
            "query_pairs": pairs,
            "full_url": str(httpx.URL(url, params=cast(Any, pairs))),
        }

    return build_rapidapi_url


def _extract_spec_from_tool_call(response: Any) -> RapidApiQuerySpec:
    tool_calls = getattr(response, "tool_calls", None)
    if not isinstance(tool_calls, list) or not tool_calls:
        raise ValueError("tool model returned no tool calls")
    first = tool_calls[0]
    if not isinstance(first, dict):
        raise ValueError("tool call payload has unexpected type")
    name = first.get("name")
    if name != "build_rapidapi_url":
        raise ValueError(f"unexpected tool called: {name!r}")
    args = first.get("args")
    if not isinstance(args, dict):
        raise ValueError("tool call args are missing or invalid")
    return RapidApiQuerySpec.model_validate(args)


def get_structured_model(
    settings: Settings | None = None,
    *,
    provider_key: str | None = None,
) -> _StructuredInvoker:
    s = settings or get_settings()
    key = provider_key or _resolve_provider(s).PROVIDER_KEY
    model = _structured_by_provider.get(key)
    if model is None:
        model = _default_structured_model(s)
        _structured_by_provider[key] = model
    return model


def set_structured_model_for_tests(
    model: _StructuredInvoker | None,
    *,
    provider_key: str | None = None,
) -> None:
    key = provider_key or jsearch.PROVIDER_KEY
    if model is None:
        _structured_by_provider.pop(key, None)
        return
    _structured_by_provider[key] = model


def reset_structured_model() -> None:
    """Clear cached structured-output chains for all providers."""
    _structured_by_provider.clear()


def validate_and_clamp_spec(
    spec: RapidApiQuerySpec,
    *,
    settings: Settings | None = None,
) -> RapidApiQuerySpec:
    s = settings or get_settings()
    provider = _resolve_provider(s)
    return provider.validate_and_clamp_spec(spec, settings=s)


def flatten_query_params(params: dict[str, Any]) -> list[tuple[str, str]]:
    """Turn validated params into httpx-friendly ``(key, str)`` pairs."""
    out: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out.append((key, "true" if value else "false"))
        elif isinstance(value, (list, tuple)):
            for item in value:
                out.append((key, str(item)))
        else:
            out.append((key, str(value)))
    return out


def build_get_url_and_params(
    spec: RapidApiQuerySpec,
    *,
    settings: Settings | None = None,
) -> tuple[str, list[tuple[str, str]]]:
    s = settings or get_settings()
    validated = validate_and_clamp_spec(spec, settings=s)
    host = str(s.RAPIDAPI_HOST).strip().rstrip("/")
    url = f"https://{host}/{validated.path}"
    pairs = flatten_query_params(validated.query_params)
    return url, pairs


def _trace_query_builder_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "keywords_count": len(inputs.get("keywords", [])),
        "has_location": bool(inputs.get("location")),
        "remote_only": bool(inputs.get("remote_only")),
        "employment_types_count": len(inputs.get("employment_types", [])),
        "has_salary_min": inputs.get("salary_min") is not None,
        "has_salary_max": inputs.get("salary_max") is not None,
    }


def _trace_query_builder_outputs(output: Any) -> dict[str, Any]:
    if isinstance(output, RapidApiQuerySpec):
        return {
            "path": output.path,
            "query_keys": sorted(output.query_params.keys()),
        }
    return {"output_type": type(output).__name__}


@traceable(
    run_type="tool",
    name="rapidapi.build_query_spec_via_llm",
    tags=["rapidapi", "query_builder"],
    process_inputs=_trace_query_builder_inputs,
    process_outputs=_trace_query_builder_outputs,
)
async def build_query_spec_via_llm(
    *,
    keywords: list[str],
    location: str | None,
    remote_only: bool,
    employment_types: list[str],
    salary_min: int | None,
    salary_max: int | None,
    settings: Settings | None = None,
) -> RapidApiQuerySpec:
    """Build one provider-specific RapidAPI query spec via LLM."""
    s = settings or get_settings()
    provider = _resolve_provider(s)
    reference = provider.REFERENCE_PATH.read_text(encoding="utf-8")
    system = provider.build_system_prompt()

    payload = {
        "keywords": keywords,
        "location": location,
        "remote_only": remote_only,
        "employment_types": employment_types,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "requested_limit": s.RAPIDAPI_JOB_FETCH_LIMIT,
    }
    human = (
        "### API reference\n\n"
        f"{reference}\n\n"
        "### User search config (JSON)\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    log_ctx = log.bind(agent_name="rapidapi_query_builder", provider=provider.PROVIDER_KEY)
    log_ctx.info("rapidapi_query_builder.llm_start")
    messages = [SystemMessage(content=system), HumanMessage(content=human)]

    spec: RapidApiQuerySpec
    try:
        tool_model = _default_tool_model(s)
        tool_response = await tool_model.ainvoke(messages)
        spec = _extract_spec_from_tool_call(tool_response)
    except Exception as exc:
        log_ctx.warning(
            "rapidapi_query_builder.tool_call_failed",
            error=str(exc),
        )
        model = get_structured_model(s, provider_key=provider.PROVIDER_KEY)
        fallback = await model.ainvoke(messages)
        if not isinstance(fallback, RapidApiQuerySpec):
            raise TypeError("structured model returned unexpected type") from exc
        spec = fallback

    validated = provider.validate_and_clamp_spec(spec, settings=s)
    url, pairs = build_get_url_and_params(validated, settings=s)
    log_ctx.info(
        "rapidapi_query_builder.full_url_built",
        full_url=str(httpx.URL(url, params=cast(Any, pairs))),
    )
    log_ctx.info("rapidapi_query_builder.llm_done", path=validated.path)
    return validated


__all__ = [
    "RapidApiQuerySpec",
    "build_get_url_and_params",
    "build_query_spec_via_llm",
    "flatten_query_params",
    "get_structured_model",
    "reset_structured_model",
    "set_structured_model_for_tests",
    "validate_and_clamp_spec",
]
