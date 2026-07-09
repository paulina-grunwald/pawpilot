"""Application settings sourced from environment / .env."""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_async_database_url(database_url: str) -> str:
    """Coerce a plain Postgres URL to the asyncpg driver used by the app.

    Managed providers (Railway, Heroku, …) inject ``DATABASE_URL`` with a
    ``postgres://`` or ``postgresql://`` scheme, but our async engine and Alembic
    both require the ``postgresql+asyncpg://`` driver. A URL that already names an
    explicit driver (e.g. ``postgresql+asyncpg://``) is left untouched.
    """
    for bare_scheme in ("postgresql://", "postgres://"):
        if database_url.startswith(bare_scheme):
            return "postgresql+asyncpg://" + database_url[len(bare_scheme) :]
    return database_url


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
    backend_base_url: str = "http://localhost:8000"

    media_root: str = "./media"

    cookie_name: str = "pawpilot_auth"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_max_age_seconds: int = 60 * 60 * 24

    jwt_lifetime_seconds: int = 60 * 60 * 24

    environment: str = "development"

    admin_ingest_token: str | None = None

    @field_validator("database_url", mode="after")
    @classmethod
    def _coerce_async_driver(cls, database_url: str) -> str:
        return normalize_async_database_url(database_url)


settings = Settings()  # type: ignore[call-arg]
