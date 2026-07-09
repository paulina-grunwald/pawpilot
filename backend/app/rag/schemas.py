"""Pydantic contracts for the RAG backbone.

`RetrievedChunk` is the load-bearing citation contract: every retrieval result
carries enough metadata for specs 010/011 to render a citation like
*"WSAVA Vaccination Guidelines 2024, §Core vaccines, p. 12"* without a second
lookup.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Authority order for advice surfaces: guideline > consensus > primary_research.
# `breed` and `food` are domain-specific lanes, not an authority ranking.
SourceTier = Literal["guideline", "consensus", "primary_research", "breed", "food"]

SizeCategory = Literal["toy", "small", "medium", "large", "giant"]
ToxicCategory = Literal["food", "plant", "medication", "household"]
ToxicSeverity = Literal["mild", "moderate", "severe", "emergency"]

RetrievalMode = Literal["dense", "hybrid", "rerank"]


class RetrievedChunk(BaseModel):
    """A single retrieved passage with the full citation payload."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    text: str
    score: float
    source_id: str
    title: str
    organization: str
    year: int | str
    url: str
    section: str
    page_start: int
    page_end: int
    source_tier: SourceTier
    license_note: str | None = None


class RagSearchRequest(BaseModel):
    """Request body for the dev/QA `POST /rag/search` probe."""

    query: str = Field(min_length=1, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
    sources: list[str] | None = None
    source_tiers: list[SourceTier] | None = None


class RagSearchResponse(BaseModel):
    results: list[RetrievedChunk]


class BreedNorm(BaseModel):
    """Physiological norms for a size category (with optional per-breed rows)."""

    size_category: SizeCategory
    resting_heart_rate_range_bpm: tuple[int, int]
    sleeping_respiratory_rate_max_bpm: int
    daily_walk_target_km_range: tuple[float, float]
    senior_age_years: int
    source_url: str
    breed: str | None = None


class ToxicSubstance(BaseModel):
    """A substance toxic to dogs, matched by name or alias at lookup time."""

    name: str
    aliases: list[str] = Field(default_factory=list)
    category: ToxicCategory
    severity: ToxicSeverity
    notes: str
    source_url: str
