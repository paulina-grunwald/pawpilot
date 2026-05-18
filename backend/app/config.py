"""Application settings sourced from environment / .env."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    jwt_secret: str
    frontend_base_url: str = "http://localhost:3000"

    cookie_name: str = "pawpilot_auth"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_max_age_seconds: int = 60 * 60 * 24

    jwt_lifetime_seconds: int = 60 * 60 * 24

    environment: str = "development"


settings = Settings()  # type: ignore[call-arg]
