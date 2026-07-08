"""Dense retrieval over the vet corpus
VetCorpusRetriever.retrieve embeds the query, runs a cosine search over the
dense vector with optional source_id / source_tier filters, and maps
each hit's payload back into a RetrievedChunk. The mode argument exists now
so 009b (hybrid) and 009c (rerank) slot in without changing callers.
"""

from __future__ import annotations

from langsmith import traceable
from qdrant_client import QdrantClient, models

from app.rag.config import RagSettings, get_rag_settings
from app.rag.embeddings import Embedder, GatewayEmbedder
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
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._default_top_k = default_top_k

    @traceable(run_type="retriever", name="vet_corpus.retrieve")
    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        sources: list[str] | None = None,
        source_tiers: list[SourceTier] | None = None,
        mode: RetrievalMode = "dense",
    ) -> list[RetrievedChunk]:
        if mode != "dense":
            raise NotImplementedError(
                f"retrieval mode {mode!r} is not available until a later phase (009b/009c)"
            )
        if (sources is not None and not sources) or (source_tiers is not None and not source_tiers):
            return []
        limit = top_k if top_k is not None else self._default_top_k
        query_vector = self._embedder.embed_query(query)
        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            using=DENSE_VECTOR,
            limit=limit,
            query_filter=_build_filter(sources, source_tiers),
            with_payload=True,
        )
        return [_to_chunk(point) for point in response.points]


def build_retriever(settings: RagSettings | None = None) -> VetCorpusRetriever:
    """Build a retriever backed by a live Qdrant + Gateway embedder."""
    resolved = settings if settings is not None else get_rag_settings()
    client = QdrantClient(url=resolved.qdrant_url, api_key=resolved.qdrant_api_key)
    return VetCorpusRetriever(
        client=client,
        embedder=GatewayEmbedder(resolved),
        collection=resolved.collection,
        default_top_k=resolved.default_top_k,
    )
