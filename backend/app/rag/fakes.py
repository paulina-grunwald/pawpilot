"""Deterministic, network-free test doubles for the RAG embedding and rerank backends."""

from __future__ import annotations

import hashlib
import math
import random

from app.rag.reranking import RerankResult


class FakeEmbedder:
    """Deterministic, network-free embedder for hermetic tests."""

    def __init__(self, dimensions: int = 16) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed)
        values = [rng.uniform(-1.0, 1.0) for _ in range(self._dimensions)]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class FakeReranker:
    """Deterministic reranker for hermetic tests.

    Scores each document by lexical overlap with the query (the fraction of query
    tokens it contains), so a test can assert a specific reorder without a network
    call. Ties break by original index to stay stable.
    """

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        query_tokens = set(query.lower().split())
        scored = [
            RerankResult(
                index=index,
                relevance_score=(
                    len(query_tokens & set(document.lower().split())) / len(query_tokens)
                    if query_tokens
                    else 0.0
                ),
            )
            for index, document in enumerate(documents)
        ]
        scored.sort(key=lambda result: (-result.relevance_score, result.index))
        return scored[:top_n]
