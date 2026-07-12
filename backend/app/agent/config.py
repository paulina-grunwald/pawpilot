"""Agent settings — reuses the Vercel AI Gateway credentials plus Tavily.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    gateway_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "VERCEL_AI_GATEWAY",
            "AI_GATEWAY_API_KEY",
            "VERCEL_OIDC_TOKEN",
        ),
    )
    gateway_base_url: str = Field(
        default="https://ai-gateway.vercel.sh/v1",
        validation_alias="RAG_GATEWAY_BASE_URL",
    )

    agent_model: str = Field(default="openai/gpt-5.4-mini", validation_alias="AGENT_MODEL")
    agent_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, validation_alias="AGENT_TEMPERATURE"
    )
    agent_max_tool_calls: int = Field(
        default=6, ge=1, le=20, validation_alias="AGENT_MAX_TOOL_CALLS"
    )

    tavily_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("TAVILY_API_KEY", "TAVILY"),
    )
    web_search_max_results: int = Field(
        default=5, ge=1, le=20, validation_alias="WEB_SEARCH_MAX_RESULTS"
    )

    memory_backend: Literal["memory", "postgres"] = Field(
        default="postgres", validation_alias="MEMORY_BACKEND"
    )
    max_dog_memories: int = Field(default=20, ge=1, le=100, validation_alias="MAX_DOG_MEMORIES")
    memory_pool_max_size: int = Field(
        default=20, ge=1, le=100, validation_alias="AGENT_MEMORY_POOL_MAX_SIZE"
    )

    @model_validator(mode="after")
    def _validate(self) -> AgentSettings:
        if not self.gateway_api_key.get_secret_value():
            raise ValueError("A Vercel AI Gateway key is required")
        if "/" not in self.agent_model:
            raise ValueError(
                "agent_model must be a provider-qualified AI Gateway id "
                f"(e.g. 'openai/...'); got {self.agent_model!r}."
            )
        return self


@lru_cache
def get_agent_settings() -> AgentSettings:
    """Return the process-wide agent settings (constructed on first use)."""
    return AgentSettings()
