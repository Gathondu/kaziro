from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class SourceAuthConfig(BaseModel):
    type: Literal["none", "bearer", "static_header", "query_param_key"] = "none"
    header_name: str | None = None
    query_param_name: str | None = None
    credential_env_var: str | None = None


class SourcePaginationConfig(BaseModel):
    type: Literal["none", "page", "offset", "cursor"] = "none"
    page_param: str | None = None
    page_size_param: str | None = None
    default_page_size: int = Field(default=10, ge=1, le=100)


class SourceProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: AnyHttpUrl
    endpoint_path: str = Field(min_length=1)
    method: Literal["GET"] = "GET"
    query_params: dict[str, str] = Field(default_factory=dict)
    pagination: SourcePaginationConfig = Field(default_factory=SourcePaginationConfig)
    auth: SourceAuthConfig = Field(default_factory=SourceAuthConfig)
    response_mapping: dict[str, str] = Field(default_factory=dict)
    confidence_score: float = Field(default=0, ge=0, le=1)
    evidence_urls: list[str] = Field(default_factory=list)

    @field_validator("endpoint_path")
    @classmethod
    def endpoint_path_starts_with_slash(cls, value: str) -> str:
        return value if value.startswith("/") else f"/{value}"


def validate_provider_config(config: dict[str, object]) -> SourceProviderConfig:
    return SourceProviderConfig.model_validate(config)


__all__ = [
    "SourceAuthConfig",
    "SourcePaginationConfig",
    "SourceProviderConfig",
    "validate_provider_config",
]
