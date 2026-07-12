"""LangSmith observability wiring."""

from __future__ import annotations

import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LANGSMITH_ENDPOINT = "https://eu.api.smith.langchain.com"
DEFAULT_LANGSMITH_PROJECT = "pawpilot-rag"


class LangSmithSettings(BaseSettings):
    """LangSmith configuration, read from .env or the real process environment."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    tracing: bool = Field(default=False, validation_alias="LANGSMITH_TRACING")
    api_key: SecretStr = Field(default=SecretStr(""), validation_alias="LANGSMITH_API_KEY")
    endpoint: str = Field(default=DEFAULT_LANGSMITH_ENDPOINT, validation_alias="LANGSMITH_ENDPOINT")
    project: str = Field(default=DEFAULT_LANGSMITH_PROJECT, validation_alias="LANGSMITH_PROJECT")


def tracing_enabled() -> bool:
    """True only when LANGSMITH_TRACING is explicitly true in the environment."""
    return os.environ.get("LANGSMITH_TRACING", "").strip().lower() == "true"


def configure_langsmith() -> bool:
    """Apply LangSmith settings to the environment. Call once at app startup.

    Pins the EU endpoint and project without overriding values already set. When
    tracing is on, LANGSMITH_TRACING is normalized to "true" (so alternate truthy
    spellings like "1" still trace) and the API key is promoted into the
    environment, which is where the LangSmith client reads it. config.tracing is
    the single source of truth for whether tracing is enabled.
    """
    config = LangSmithSettings()
    os.environ.setdefault("LANGSMITH_ENDPOINT", config.endpoint)
    os.environ.setdefault("LANGSMITH_PROJECT", config.project)
    if config.tracing:
        os.environ["LANGSMITH_TRACING"] = "true"
        key = config.api_key.get_secret_value()
        if key:
            os.environ.setdefault("LANGSMITH_API_KEY", key)
        else:
            print("LANGSMITH_TRACING is on but LANGSMITH_API_KEY is empty; traces will not export.")
    return config.tracing
