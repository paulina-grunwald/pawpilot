"""RAG settings — Vercel AI Gateway + Qdrant configuration.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    gateway_api_key: str = Field(
        default="",
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

    embed_model: str = Field(
        default="openai/text-embedding-3-small",
        validation_alias="RAG_EMBED_MODEL",
    )
    embed_dimensions: int = Field(default=1536, validation_alias="RAG_EMBED_DIMENSIONS")
    gen_model: str = Field(
        default="openai/gpt-5.4-mini",
        validation_alias="RAG_GEN_MODEL",
    )

    qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, validation_alias="QDRANT_API_KEY")
    collection: str = Field(default="vet_corpus", validation_alias="RAG_COLLECTION")

    default_top_k: int = Field(default=8, ge=1, le=20, validation_alias="RAG_DEFAULT_TOP_K")
    fused_candidates: int = Field(default=25, validation_alias="RAG_FUSED_CANDIDATES")

    @model_validator(mode="after")
    def _validate(self) -> RagSettings:
        if not self.gateway_api_key:
            raise ValueError("A Vercel AI Gateway key is required")

        for role, model_id in (("embed_model", self.embed_model), ("gen_model", self.gen_model)):
            if "/" not in model_id:
                raise ValueError(
                    f"{role} must be a provider-qualified AI Gateway id (e.g. 'openai/...'); "
                    f"got {model_id!r}."
                )
        return self


@lru_cache
def get_rag_settings() -> RagSettings:
    """Return the process-wide RAG settings (constructed on first use)."""
    return RagSettings()
