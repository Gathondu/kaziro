from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

_HEADER_NAME_PATTERN = r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$"
_ENV_VAR_PATTERN = r"^[A-Z][A-Z0-9_]*$"
_RESPONSE_LIST_PATH_PATTERN = r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$"
_SENSITIVE_HEADER_PARTS = ("authorization", "api-key", "apikey", "token", "secret")


class SourceAuthConfig(BaseModel):
    type: Literal["none", "bearer", "static_header", "query_param_key"] = "none"
    header_name: str | None = None
    query_param_name: str | None = None
    credential_env_var: str | None = None

    @model_validator(mode="after")
    def validate_required_auth_fields(self) -> SourceAuthConfig:
        if self.type == "none":
            return self
        if not self.credential_env_var:
            raise ValueError("credential_env_var is required for authenticated providers.")
        if self.type == "static_header" and not self.header_name:
            raise ValueError("header_name is required for static_header authentication.")
        if self.type == "query_param_key" and not self.query_param_name:
            raise ValueError("query_param_name is required for query_param_key authentication.")
        return self


class SourcePaginationConfig(BaseModel):
    type: Literal["none", "page", "offset", "cursor"] = "none"
    page_param: str | None = None
    page_size_param: str | None = None
    default_page_size: int = Field(default=10, ge=1, le=100)


class SourceRequestHeaderConfig(BaseModel):
    name: str = Field(min_length=1, pattern=_HEADER_NAME_PATTERN)
    value: str | None = None
    value_env_var: str | None = Field(default=None, pattern=_ENV_VAR_PATTERN)

    @model_validator(mode="after")
    def validate_value_source(self) -> SourceRequestHeaderConfig:
        if (self.value is None) == (self.value_env_var is None):
            raise ValueError("Set exactly one of value or value_env_var.")
        if self.value is not None:
            if "\r" in self.value or "\n" in self.value:
                raise ValueError("Header values cannot contain newlines.")
            normalized_name = self.name.lower()
            if any(part in normalized_name for part in _SENSITIVE_HEADER_PARTS):
                raise ValueError("Sensitive header values must use value_env_var.")
        return self


class SourceProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: AnyHttpUrl
    endpoint_path: str = Field(min_length=1)
    method: Literal["GET"] = "GET"
    query_params: dict[str, str] = Field(default_factory=dict)
    pagination: SourcePaginationConfig = Field(default_factory=SourcePaginationConfig)
    auth: SourceAuthConfig = Field(default_factory=SourceAuthConfig)
    request_headers: list[SourceRequestHeaderConfig] = Field(default_factory=list)
    smoke_test_params: dict[str, str] = Field(default_factory=dict)
    response_list_path: str | None = Field(default=None, pattern=_RESPONSE_LIST_PATH_PATTERN)
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
    "SourceRequestHeaderConfig",
    "validate_provider_config",
]
