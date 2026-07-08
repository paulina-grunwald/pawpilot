"""Embedding via the Vercel AI Gateway (OpenAI-compatible).

A raw ``openai.OpenAI`` client pointed at the Gateway, a provider-qualified
model id, and the model's native dimensions (no
``dimensions=`` argument). `FakeEmbedder` is the deterministic test double —
identical text always maps to the same unit vector, so a query for a chunk's
exact text ranks that chunk first.
"""

from __future__ import annotations

import hashlib
import math
import random
from typing import Protocol

from openai import OpenAI

from app.rag.config import RagSettings

DEFAULT_EMBED_BATCH_SIZE = 128


class Embedder(Protocol):
    """Structural interface for the embedding backends used by the retriever."""

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class GatewayEmbedder:
    """Embeds via OpenAI models through the Vercel AI Gateway."""

    def __init__(
        self, settings: RagSettings, *, batch_size: int = DEFAULT_EMBED_BATCH_SIZE
    ) -> None:
        self._client = OpenAI(
            api_key=settings.gateway_api_key,
            base_url=settings.gateway_base_url,
        )
        self._model = settings.embed_model
        self._dimensions = settings.embed_dimensions
        self._batch_size = batch_size

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = self._client.embeddings.create(model=self._model, input=batch)
            # The API does not guarantee response order; each item carries its input index.
            vectors.extend(
                item.embedding for item in sorted(response.data, key=lambda item: item.index)
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


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
