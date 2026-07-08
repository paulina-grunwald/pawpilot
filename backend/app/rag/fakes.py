"""Deterministic, network-free test doubles for the RAG embedding backends.

`FakeEmbedder` implements the `Embedder` Protocol without any network calls, so tests, local dev, and eval runs can exercise the ingest/retrieve pipeline withno API key and no flakiness. Identical text always maps to the same unit vector, so a query for a chunk's exact text ranks that chunk first.
"""

from __future__ import annotations

import hashlib
import math
import random


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
