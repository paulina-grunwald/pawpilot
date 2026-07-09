from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.rag.schemas import BreedNorm, RagSearchRequest, RetrievedChunk, ToxicSubstance


def make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="wsava-vaccination-2024:3",
        text="Core vaccines are recommended for all dogs.",
        score=0.81,
        source_id="wsava-vaccination-2024",
        title="Vaccination Guidelines",
        organization="WSAVA",
        year=2024,
        url="https://example.org/wsava.pdf",
        section="Core vaccines",
        page_start=12,
        page_end=12,
        source_tier="guideline",
    )


def test_retrieved_chunk_round_trips() -> None:
    chunk = make_chunk()
    dumped = chunk.model_dump()
    assert dumped["source_id"] == "wsava-vaccination-2024"
    assert dumped["source_tier"] == "guideline"
    assert chunk.license_note is None


def test_retrieved_chunk_is_frozen() -> None:
    chunk = make_chunk()
    with pytest.raises(ValidationError):
        chunk.score = 0.1  # frozen model — assignment is rejected at runtime


def test_retrieved_chunk_accepts_string_year() -> None:
    chunk = RetrievedChunk(
        chunk_id="c",
        text="t",
        score=0.0,
        source_id="s",
        title="T",
        organization="Org",
        year="n.d.",
        url="https://x",
        section="",
        page_start=1,
        page_end=2,
        source_tier="primary_research",
    )
    assert chunk.year == "n.d."


def test_retrieved_chunk_rejects_unknown_tier() -> None:
    with pytest.raises(ValidationError):
        RetrievedChunk(
            chunk_id="c",
            text="t",
            score=0.0,
            source_id="s",
            title="T",
            organization="Org",
            year=2020,
            url="https://x",
            section="",
            page_start=1,
            page_end=1,
            source_tier="opinion",  # type: ignore[arg-type]
        )


def test_search_request_defaults() -> None:
    request = RagSearchRequest(query="how often to vaccinate")
    assert request.top_k is None
    assert request.sources is None
    assert request.source_tiers is None


@pytest.mark.parametrize("query", ["", "x" * 501])
def test_search_request_query_bounds(query: str) -> None:
    with pytest.raises(ValidationError):
        RagSearchRequest(query=query)


@pytest.mark.parametrize("top_k", [0, 21])
def test_search_request_top_k_bounds(top_k: int) -> None:
    with pytest.raises(ValidationError):
        RagSearchRequest(query="hi", top_k=top_k)


def test_breed_norm_parses_tuples() -> None:
    norm = BreedNorm(
        size_category="medium",
        resting_heart_rate_range_bpm=(70, 120),
        sleeping_respiratory_rate_max_bpm=30,
        daily_walk_target_km_range=(3.0, 6.0),
        senior_age_years=8,
        source_url="https://example.org/norms",
    )
    assert norm.resting_heart_rate_range_bpm == (70, 120)
    assert norm.breed is None


def test_toxic_substance_defaults_aliases() -> None:
    substance = ToxicSubstance(
        name="xylitol",
        category="food",
        severity="emergency",
        notes="Causes hypoglycemia and liver failure.",
        source_url="https://example.org/tox",
    )
    assert substance.aliases == []
