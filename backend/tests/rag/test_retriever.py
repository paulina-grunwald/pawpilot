from __future__ import annotations

import pytest
from qdrant_client import QdrantClient, models

from app.rag import retriever as retriever_module
from app.rag.config import RagSettings
from app.rag.fakes import FakeEmbedder, FakeReranker
from app.rag.reranking import (
    CohereGatewayReranker,
    Reranker,
    RerankResponse,
    RerankResult,
    RerankUnavailableError,
)
from app.rag.retriever import VetCorpusRetriever, build_retriever
from app.rag.schemas import RetrievalMode, RetrievedChunk
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


def _make_retriever(
    *,
    default_mode: RetrievalMode = "dense",
    reranker: Reranker | None = None,
    rerank_candidates: int = 25,
) -> VetCorpusRetriever:
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
    return VetCorpusRetriever(
        client,
        embedder,
        _COLLECTION,
        default_top_k=8,
        default_mode=default_mode,
        reranker=reranker,
        rerank_candidates=rerank_candidates,
    )


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


def test_hybrid_mode_still_raises() -> None:
    retriever = _make_retriever()
    with pytest.raises(NotImplementedError):
        retriever.retrieve("x", mode="hybrid")


# --------------------------------------------------------------------------- #
# Rerank mode
# --------------------------------------------------------------------------- #


class _RecordingReranker:
    """Reranker that records the documents it saw and returns them reversed."""

    def __init__(self) -> None:
        self.documents: list[str] = []

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        self.documents = list(documents)
        order = list(reversed(range(len(documents))))[:top_n]
        return [
            RerankResult(index=index, relevance_score=float(len(documents) - index))
            for index in order
        ]


class _RaisingReranker:
    """Reranker that fails if invoked, to prove a code path never reaches it."""

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        raise AssertionError("the reranker should not have been called")


class _OutOfRangeReranker:
    """Reranker that returns one valid index and one out-of-range index."""

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        return [
            RerankResult(index=len(documents) + 5, relevance_score=0.99),
            RerankResult(index=0, relevance_score=0.42),
        ]


class _NegativeIndexReranker:
    """Reranker that returns a negative index alongside a valid one."""

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        return [
            RerankResult(index=-1, relevance_score=0.99),
            RerankResult(index=0, relevance_score=0.42),
        ]


class _MalformedResponseReranker:
    """Reranker whose response fails ``RerankResponse`` validation."""

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        return RerankResponse.model_validate({"unexpected": []}).results


def test_rerank_mode_reorders_and_annotates_chunks() -> None:
    retriever = _make_retriever(
        default_mode="rerank", reranker=FakeReranker(), rerank_candidates=25
    )
    results = retriever.retrieve("dental cleaning frequency recommendations", top_k=3)
    top = results[0]
    # FakeReranker scores by query overlap, so the exact-text doc ranks first.
    assert top.source_id == "wsava-dental"
    assert top.rerank_score == pytest.approx(1.0)
    assert top.pre_rerank_rank is not None
    # every reranked chunk carries the cross-encoder annotation.
    assert all(chunk.rerank_score is not None for chunk in results)
    assert all(chunk.pre_rerank_rank is not None for chunk in results)


def test_rerank_applies_reranker_order_and_records_pre_rerank_rank() -> None:
    recorder = _RecordingReranker()
    retriever = _make_retriever(default_mode="rerank", reranker=recorder, rerank_candidates=25)
    results = retriever.retrieve("anything", top_k=3)
    order = list(reversed(range(len(recorder.documents))))
    assert [chunk.text for chunk in results] == [recorder.documents[index] for index in order]
    assert [chunk.pre_rerank_rank for chunk in results] == order


def test_rerank_trims_to_top_k() -> None:
    retriever = _make_retriever(
        default_mode="rerank", reranker=FakeReranker(), rerank_candidates=25
    )
    assert len(retriever.retrieve("anything", top_k=2)) == 2


def test_dense_mode_leaves_rerank_fields_unset() -> None:
    retriever = _make_retriever()
    chunk = retriever.retrieve("dental", top_k=1)[0]
    assert chunk.rerank_score is None
    assert chunk.pre_rerank_rank is None


def test_rerank_without_a_reranker_raises() -> None:
    retriever = _make_retriever(default_mode="rerank")  # no reranker wired
    with pytest.raises(ValueError, match="requires a reranker"):
        retriever.retrieve("anything")


def test_explicit_rerank_mode_reaches_rerank_path() -> None:
    # A dense-default retriever with no reranker must still honour an explicit
    # mode override, proving the mode argument (not just default_mode) routes.
    retriever = _make_retriever()
    with pytest.raises(ValueError, match="requires a reranker"):
        retriever.retrieve("anything", mode="rerank")


def test_rerank_over_fetches_exactly_rerank_candidates() -> None:
    # The reranker must see rerank_candidates dense hits (not top_k, not the whole
    # corpus): three distinct numbers -> corpus 3, candidates 2, top_k 1.
    recorder = _RecordingReranker()
    retriever = _make_retriever(default_mode="rerank", reranker=recorder, rerank_candidates=2)
    results = retriever.retrieve("anything", top_k=1)
    assert len(recorder.documents) == 2
    assert len(results) == 1


def test_rerank_skips_out_of_range_reranker_indices() -> None:
    retriever = _make_retriever(default_mode="rerank", reranker=_OutOfRangeReranker())
    results = retriever.retrieve("anything", top_k=3)
    # The out-of-range index is dropped; the single valid index survives.
    assert len(results) == 1
    assert results[0].pre_rerank_rank == 0


def test_rerank_drops_negative_reranker_index_without_wrapping() -> None:
    retriever = _make_retriever(default_mode="rerank", reranker=_NegativeIndexReranker())
    results = retriever.retrieve("anything", top_k=3)
    assert len(results) == 1
    assert results[0].pre_rerank_rank == 0


def test_rerank_returns_empty_when_dense_search_has_no_hits() -> None:
    retriever = _make_retriever(default_mode="rerank", reranker=_RaisingReranker())
    assert retriever.retrieve("anything", sources=["does-not-exist"]) == []


def test_rerank_malformed_response_raises_rerank_unavailable_not_validation_error() -> None:
    retriever = _make_retriever(default_mode="rerank", reranker=_MalformedResponseReranker())
    with pytest.raises(RerankUnavailableError):
        retriever.retrieve("anything", top_k=1)


def test_unknown_mode_raises_value_error() -> None:
    retriever = _make_retriever()
    with pytest.raises(ValueError, match="unknown retrieval mode"):
        retriever.retrieve("anything", mode="sparse")


# build_retriever wiring


def _fake_settings(default_mode: RetrievalMode = "dense") -> RagSettings:
    return RagSettings(
        gateway_api_key="test-key",
        gateway_base_url="https://ai-gateway.vercel.sh/v1",
        rerank_model="cohere/rerank-v3.5",
        default_mode=default_mode,
    )


def _stub_live_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep build_retriever hermetic: no Qdrant connection, no Gateway embedder.
    monkeypatch.setattr(retriever_module, "QdrantClient", lambda **kwargs: object())
    monkeypatch.setattr(retriever_module, "GatewayEmbedder", lambda settings: object())


def test_build_retriever_wires_reranker_only_for_rerank_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_live_backends(monkeypatch)
    settings = _fake_settings()

    rerank_retriever = build_retriever(settings, mode="rerank")
    assert isinstance(rerank_retriever._reranker, CohereGatewayReranker)
    assert rerank_retriever._default_mode == "rerank"

    dense_retriever = build_retriever(settings, mode="dense")
    assert dense_retriever._reranker is None
    assert dense_retriever._default_mode == "dense"


def test_build_retriever_mode_argument_overrides_settings_default_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_live_backends(monkeypatch)
    # settings default is rerank, but an explicit dense mode must win (no reranker).
    dense_over_rerank = build_retriever(_fake_settings(default_mode="rerank"), mode="dense")
    assert dense_over_rerank._default_mode == "dense"
    assert dense_over_rerank._reranker is None
    # and the reverse: settings default is dense, explicit rerank wins (reranker wired).
    rerank_over_dense = build_retriever(_fake_settings(default_mode="dense"), mode="rerank")
    assert rerank_over_dense._default_mode == "rerank"
    assert isinstance(rerank_over_dense._reranker, CohereGatewayReranker)


def test_build_retriever_defaults_mode_to_settings_when_unspecified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_live_backends(monkeypatch)
    retriever = build_retriever(_fake_settings(default_mode="rerank"))
    assert retriever._default_mode == "rerank"
    assert isinstance(retriever._reranker, CohereGatewayReranker)
