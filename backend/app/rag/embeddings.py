"""Embedding via the Vercel AI Gateway (OpenAI-compatible).

A raw ``openai.OpenAI`` client pointed at the Gateway, a provider-qualified
model id, and the model's native dimensions (no ``dimensions=`` argument).
The deterministic, network-free test double lives in `app.rag.fakes`.
"""

from __future__ import annotations

from typing import Protocol

from openai import OpenAI

from app.rag.config import RagSettings


class Embedder(Protocol):
    """Structural interface for the embedding backends used by the retriever."""

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class GatewayEmbedder:
    """Embeds via OpenAI models through the Vercel AI Gateway."""

    def __init__(self, settings: RagSettings, *, batch_size: int | None = None) -> None:
        self._client = OpenAI(api_key=settings.gateway_api_key, base_url=settings.gateway_base_url)
        self._model = settings.embed_model
        self._dimensions = settings.embed_dimensions
        self._batch_size = batch_size if batch_size is not None else settings.embed_batch_size

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

            vectors.extend(
                item.embedding for item in sorted(response.data, key=lambda item: item.index)
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
