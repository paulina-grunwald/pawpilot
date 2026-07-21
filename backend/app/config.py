"""Application settings sourced from environment / .env."""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator, model_validator
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

    media_backend: Literal["local", "s3"] = "local"
    media_root: str = "./media"

    s3_endpoint_url: str | None = None
    s3_bucket: str = "pawpilot-media"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "us-east-1"

    cookie_name: str = "pawpilot_auth"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_max_age_seconds: int = 60 * 60 * 24

    jwt_lifetime_seconds: int = 60 * 60 * 24

    environment: str = "development"

    admin_ingest_token: str | None = None

    # Rate limiting. The agent routes call the paid LLM gateway, so an authenticated
    # user (or a leaked token) hammering them burns real money; these cap that. Keyed
    # per authenticated user. Disabled under test so suites can call freely.
    rate_limit_enabled: bool = True
    agent_rate_limit: str = "30/minute"

    @field_validator("database_url", mode="after")
    @classmethod
    def _coerce_async_driver(cls, database_url: str) -> str:
        return normalize_async_database_url(database_url)

    @model_validator(mode="after")
    def _s3_backend_requires_credentials(self) -> Settings:
        if self.media_backend == "s3":
            missing = [
                name.upper()
                for name in ("s3_endpoint_url", "s3_access_key_id", "s3_secret_access_key")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"MEDIA_BACKEND=s3 requires {', '.join(missing)}")
        return self


settings = Settings()  # type: ignore[call-arg]
