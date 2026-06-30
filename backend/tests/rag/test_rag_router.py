from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.main import app
from app.rag.router import get_retriever
from app.rag.schemas import RetrievalMode, RetrievedChunk, SourceTier


def _payload_validation_error() -> ValidationError:
    """A real ValidationError, as `_to_chunk` raises on a corrupt Qdrant payload."""
    try:
        RetrievedChunk.model_validate({})
    except ValidationError as error:
        return error
    raise AssertionError("expected RetrievedChunk validation to fail")


class _FakeRetriever:
    def __init__(
        self,
        chunks: list[RetrievedChunk] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._chunks = chunks or []
        self._error = error

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        sources: list[str] | None = None,
        source_tiers: list[SourceTier] | None = None,
        mode: RetrievalMode = "dense",
    ) -> list[RetrievedChunk]:
        if self._error is not None:
            raise self._error
        return self._chunks


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="wsava-vaccination-2024:1",
        text="Adult dogs need a leptospirosis booster annually.",
        score=0.87,
        source_id="wsava-vaccination-2024",
        title="Vaccination Guidelines",
        organization="WSAVA",
        year=2024,
        url="https://example.org/wsava.pdf",
        section="Core vaccines",
        page_start=12,
        page_end=12,
        source_tier="guideline",
    )


@pytest.fixture
def install_retriever() -> Iterator[Callable[[_FakeRetriever], None]]:
    def _install(retriever: _FakeRetriever) -> None:
        app.dependency_overrides[get_retriever] = lambda: retriever

    yield _install
    app.dependency_overrides.pop(get_retriever, None)


async def test_search_returns_results(
    authenticated_client: AsyncClient,
    install_retriever: Callable[[_FakeRetriever], None],
) -> None:
    install_retriever(_FakeRetriever(chunks=[_chunk()]))
    response = await authenticated_client.post(
        "/rag/search", json={"query": "leptospirosis booster"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["source_id"] == "wsava-vaccination-2024"
    assert result["source_tier"] == "guideline"
    assert result["page_start"] == 12


async def test_search_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/rag/search", json={"query": "anything"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload", [{"query": ""}, {"query": "ok", "top_k": 0}, {"query": "ok", "top_k": 99}]
)
async def test_search_validates_payload(
    authenticated_client: AsyncClient,
    install_retriever: Callable[[_FakeRetriever], None],
    payload: dict[str, object],
) -> None:
    install_retriever(_FakeRetriever())
    response = await authenticated_client.post("/rag/search", json=payload)
    assert response.status_code == 422


async def test_search_returns_503_when_retriever_fails(
    authenticated_client: AsyncClient,
    install_retriever: Callable[[_FakeRetriever], None],
) -> None:
    install_retriever(_FakeRetriever(error=RuntimeError("qdrant down")))
    response = await authenticated_client.post("/rag/search", json={"query": "anything"})
    assert response.status_code == 503
    assert response.json()["detail"] == "RAG_UNAVAILABLE"


async def test_search_returns_500_on_corrupt_payload(
    authenticated_client: AsyncClient,
    install_retriever: Callable[[_FakeRetriever], None],
) -> None:
    install_retriever(_FakeRetriever(error=_payload_validation_error()))
    response = await authenticated_client.post("/rag/search", json={"query": "anything"})
    assert response.status_code == 500
    assert response.json()["detail"] == "RAG_PAYLOAD_CORRUPT"
