from __future__ import annotations

from app.rag.schemas import RetrievedChunk
from evals.rag.golden import load_golden, recall_at_k


def _chunk(source_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{source_id}:0",
        text="text",
        score=0.5,
        source_id=source_id,
        title="Title",
        organization="Org",
        year=2024,
        url="https://example.org",
        section="Section",
        page_start=1,
        page_end=1,
        source_tier="guideline",
    )


def test_recall_hits_when_expected_in_top_k() -> None:
    retrieved = [_chunk("a"), _chunk("b"), _chunk("target")]
    assert recall_at_k(["target"], retrieved, 3) == 1.0


def test_recall_respects_k_cutoff() -> None:
    retrieved = [_chunk("a"), _chunk("b"), _chunk("target")]
    assert recall_at_k(["target"], retrieved, 2) == 0.0  # target sits at rank 3


def test_recall_miss_returns_zero() -> None:
    retrieved = [_chunk("a"), _chunk("b")]
    assert recall_at_k(["target"], retrieved, 10) == 0.0


def test_recall_matches_any_expected_source() -> None:
    retrieved = [_chunk("x"), _chunk("b")]
    assert recall_at_k(["a", "b"], retrieved, 5) == 1.0


def test_real_golden_set_loads() -> None:
    golden = load_golden()
    assert len(golden) >= 15
    assert all(item.query for item in golden)
    assert all(item.expected_source_ids for item in golden)
