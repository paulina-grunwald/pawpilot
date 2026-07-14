"""Cross-encoder reranking over dense candidates"""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict

from app.rag.config import RagSettings

_REQUEST_TIMEOUT_SECONDS = 30.0


class RerankResult(BaseModel):
    """One reranked document: its position in the input list and its score."""

    model_config = ConfigDict(frozen=True)

    index: int
    relevance_score: float


class Reranker(Protocol):
    """Re-scores (query, document) pairs and returns them ordered best-first."""

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]: ...


def _rerank_endpoint(gateway_base_url: str) -> str:
    """Derive the ``/v2/rerank`` URL from the gateway base (which ends in ``/v1``).

    Replaces only the trailing ``/v1`` version segment so a base URL carrying a
    path prefix (a reverse-proxied gateway) keeps that prefix.
    """
    parts = urlsplit(gateway_base_url)
    base_path = parts.path.rstrip("/").removesuffix("/v1")
    return urlunsplit((parts.scheme, parts.netloc, f"{base_path}/v2/rerank", "", ""))


class CohereGatewayReranker:
    """Cohere Rerank via the Vercel AI Gateway (``POST /v2/rerank``)."""

    def __init__(self, settings: RagSettings, *, client: httpx.Client | None = None) -> None:
        self._model = settings.rerank_model
        self._endpoint = _rerank_endpoint(settings.gateway_base_url)
        self._api_key = settings.gateway_api_key
        self._client = (
            client if client is not None else httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS)
        )

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        if not documents:
            return []
        response = self._client.post(
            self._endpoint,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "query": query,
                "documents": documents,
                "top_n": min(top_n, len(documents)),
            },
        )
        response.raise_for_status()
        payload = response.json()
        return [
            RerankResult(index=item["index"], relevance_score=item["relevance_score"])
            for item in payload["results"]
        ]
