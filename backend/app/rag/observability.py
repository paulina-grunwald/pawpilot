"""LangSmith observability wiring"""

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

    config = LangSmithSettings()
    os.environ.setdefault("LANGSMITH_ENDPOINT", config.endpoint)
    os.environ.setdefault("LANGSMITH_PROJECT", config.project)
    if config.tracing:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        key = config.api_key.get_secret_value()
        if key:
            os.environ.setdefault("LANGSMITH_API_KEY", key)
        else:
            print("LANGSMITH_TRACING is on but LANGSMITH_API_KEY is empty; traces will not export.")
    return tracing_enabled()
