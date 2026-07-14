"""Retrieval over the vet corpus (dense, with an optional rerank stage).

VetCorpusRetriever.retrieve embeds the query, runs a cosine search over the
dense vector with optional source_id / source_tier filters, and maps each hit's
payload back into a RetrievedChunk.
"""

from __future__ import annotations

from langsmith import traceable
from qdrant_client import QdrantClient, models

from app.rag.config import RagSettings, get_rag_settings
from app.rag.embeddings import Embedder, GatewayEmbedder
from app.rag.reranking import CohereGatewayReranker, Reranker
from app.rag.schemas import RetrievalMode, RetrievedChunk, SourceTier
from app.rag.store import DENSE_VECTOR


def _build_filter(
    sources: list[str] | None,
    source_tiers: list[SourceTier] | None,
) -> models.Filter | None:
    conditions: list[models.Condition] = []
    if sources:
        conditions.append(
            models.FieldCondition(key="source_id", match=models.MatchAny(any=list(sources)))
        )
    if source_tiers:
        conditions.append(
            models.FieldCondition(
                key="source_tier",
                match=models.MatchAny(any=[str(tier) for tier in source_tiers]),
            )
        )
    if not conditions:
        return None
    return models.Filter(must=conditions)


def _to_chunk(point: models.ScoredPoint) -> RetrievedChunk:
    payload = dict(point.payload or {})
    payload["score"] = point.score
    return RetrievedChunk.model_validate(payload)


class VetCorpusRetriever:
    """Retrieves citation-carrying chunks from the ``vet_corpus`` collection."""

    def __init__(
        self,
        client: QdrantClient,
        embedder: Embedder,
        collection: str,
        default_top_k: int = 8,
        *,
        default_mode: RetrievalMode = "dense",
        reranker: Reranker | None = None,
        rerank_candidates: int = 25,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._default_top_k = default_top_k
        self._default_mode = default_mode
        self._reranker = reranker
        self._rerank_candidates = rerank_candidates

    @traceable(run_type="retriever", name="vet_corpus.retrieve")
    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        sources: list[str] | None = None,
        source_tiers: list[SourceTier] | None = None,
        mode: RetrievalMode | None = None,
    ) -> list[RetrievedChunk]:
        resolved_mode = mode if mode is not None else self._default_mode
        if resolved_mode == "hybrid":
            raise NotImplementedError("retrieval mode 'hybrid' is not available (deferred to 009b)")
        if resolved_mode not in ("dense", "rerank"):
            raise ValueError(f"unknown retrieval mode {resolved_mode!r}")
        if (sources is not None and not sources) or (source_tiers is not None and not source_tiers):
            return []
        limit = top_k if top_k is not None else self._default_top_k
        query_filter = _build_filter(sources, source_tiers)
        if resolved_mode == "rerank":
            return self._rerank_search(query, limit, query_filter)
        return self._dense_search(query, limit, query_filter)

    def _dense_search(
        self, query: str, limit: int, query_filter: models.Filter | None
    ) -> list[RetrievedChunk]:
        query_vector = self._embedder.embed_query(query)
        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            using=DENSE_VECTOR,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [_to_chunk(point) for point in response.points]

    def _rerank_search(
        self, query: str, top_k: int, query_filter: models.Filter | None
    ) -> list[RetrievedChunk]:
        if self._reranker is None:
            raise ValueError(
                "rerank mode requires a reranker; use build_retriever(mode='rerank') to wire one"
            )
        candidates = self._dense_search(query, self._rerank_candidates, query_filter)
        if not candidates:
            return []
        results = self._reranker.rerank(query, [chunk.text for chunk in candidates], top_n=top_k)
        # Skip any index a misbehaving reranker returns outside the candidate range,
        # so one malformed row cannot crash the whole retrieval with an IndexError.
        return [
            candidates[result.index].model_copy(
                update={"rerank_score": result.relevance_score, "pre_rerank_rank": result.index}
            )
            for result in results
            if 0 <= result.index < len(candidates)
        ]


def build_retriever(
    settings: RagSettings | None = None, *, mode: RetrievalMode | None = None
) -> VetCorpusRetriever:
    """Build a retriever backed by a live Qdrant + Gateway embedder.

    ``mode`` overrides ``settings.default_mode``; ``mode="rerank"`` wires the
    Cohere-via-Gateway reranker so the retriever re-scores its dense candidates.
    """
    resolved = settings if settings is not None else get_rag_settings()
    resolved_mode: RetrievalMode = mode if mode is not None else resolved.default_mode
    client = QdrantClient(url=resolved.qdrant_url, api_key=resolved.qdrant_api_key)
    reranker: Reranker | None = (
        CohereGatewayReranker(resolved) if resolved_mode == "rerank" else None
    )
    return VetCorpusRetriever(
        client=client,
        embedder=GatewayEmbedder(resolved),
        collection=resolved.collection,
        default_top_k=resolved.default_top_k,
        default_mode=resolved_mode,
        reranker=reranker,
        rerank_candidates=resolved.rerank_candidates,
    )
