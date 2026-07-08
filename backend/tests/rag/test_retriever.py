from __future__ import annotations

import pytest
from qdrant_client import QdrantClient, models

from app.rag.fakes import FakeEmbedder
from app.rag.retriever import VetCorpusRetriever
from app.rag.schemas import RetrievedChunk
from app.rag.store import DENSE_VECTOR, chunk_point_id, ensure_collection


pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect")

_DIM = 16
_COLLECTION = "test_corpus"

_DOCS: tuple[tuple[str, str, str], ...] = (
    ("leptospirosis booster timing for adult dogs", "wsava-vaccination-2024", "guideline"),
    ("dental cleaning frequency recommendations", "wsava-dental", "guideline"),
    ("retrospective study of MDR1 prevalence in herding breeds", "breed-aussie-mdr1", "breed"),
)


def _payload(chunk_id: str, text: str, source_id: str, source_tier: str) -> dict[str, object]:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "source_id": source_id,
        "title": "Document Title",
        "organization": "WSAVA",
        "year": 2024,
        "url": "https://example.org/doc.pdf",
        "section": "Section",
        "page_start": 1,
        "page_end": 1,
        "source_tier": source_tier,
        "license_note": None,
    }


def _make_retriever() -> VetCorpusRetriever:
    client = QdrantClient(":memory:")
    embedder = FakeEmbedder(_DIM)
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)
    points: list[models.PointStruct] = []
    for index, (text, source_id, tier) in enumerate(_DOCS):
        points.append(
            models.PointStruct(
                id=chunk_point_id(source_id, index, text),
                vector={DENSE_VECTOR: embedder.embed_query(text)},
                payload=_payload(f"{source_id}:{index}", text, source_id, tier),
            )
        )
    client.upsert(collection_name=_COLLECTION, points=points)
    return VetCorpusRetriever(client, embedder, _COLLECTION, default_top_k=8)


def test_retrieve_returns_citation_chunks() -> None:
    retriever = _make_retriever()
    results = retriever.retrieve("leptospirosis booster timing for adult dogs", top_k=1)
    assert len(results) == 1
    chunk = results[0]
    assert isinstance(chunk, RetrievedChunk)
    assert chunk.source_id == "wsava-vaccination-2024"
    assert chunk.source_tier == "guideline"
    assert chunk.title == "Document Title"
    assert chunk.score > 0.99  # exact-text query -> near-perfect cosine


def test_top_k_limits_results() -> None:
    retriever = _make_retriever()
    assert len(retriever.retrieve("anything", top_k=2)) == 2


def test_default_top_k_when_unset() -> None:
    retriever = _make_retriever()
    # default_top_k is 8 but only 3 docs exist
    assert len(retriever.retrieve("anything")) == 3


def test_sources_filter_restricts_results() -> None:
    retriever = _make_retriever()
    results = retriever.retrieve("dental", sources=["wsava-dental"])
    assert results
    assert all(chunk.source_id == "wsava-dental" for chunk in results)


def test_source_tiers_filter_restricts_results() -> None:
    retriever = _make_retriever()
    results = retriever.retrieve("study", source_tiers=["breed"])
    assert results
    assert all(chunk.source_tier == "breed" for chunk in results)


def test_empty_sources_list_returns_nothing() -> None:
    retriever = _make_retriever()
    # An explicit empty allow-list means "no source allowed" — not "all sources".
    assert retriever.retrieve("anything", sources=[]) == []


def test_empty_source_tiers_list_returns_nothing() -> None:
    retriever = _make_retriever()
    assert retriever.retrieve("anything", source_tiers=[]) == []


def test_none_filters_search_whole_corpus() -> None:
    retriever = _make_retriever()
    assert len(retriever.retrieve("anything", sources=None, source_tiers=None)) == 3


def test_unsupported_mode_raises() -> None:
    retriever = _make_retriever()
    with pytest.raises(NotImplementedError):
        retriever.retrieve("x", mode="hybrid")
