"""Tests for the reranking backends.

FakeReranker and the endpoint/parse logic are pure and network-free. The
CohereGatewayReranker HTTP path is driven with an httpx MockTransport, so the
request shape and response parsing are pinned without a live Gateway call.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from app.rag.config import RagSettings
from app.rag.fakes import FakeReranker
from app.rag.reranking import CohereGatewayReranker, RerankResult, _rerank_endpoint


def _settings() -> RagSettings:
    return RagSettings(
        gateway_api_key="test-key",
        gateway_base_url="https://ai-gateway.vercel.sh/v1",
        rerank_model="cohere/rerank-v3.5",
    )


# --------------------------------------------------------------------------- #
# _rerank_endpoint
# --------------------------------------------------------------------------- #


def test_rerank_endpoint_derived_from_v1_base() -> None:
    assert (
        _rerank_endpoint("https://ai-gateway.vercel.sh/v1")
        == "https://ai-gateway.vercel.sh/v2/rerank"
    )


def test_rerank_endpoint_ignores_trailing_slash() -> None:
    assert _rerank_endpoint("https://gw.example.com/v1/") == "https://gw.example.com/v2/rerank"


def test_rerank_endpoint_preserves_a_path_prefix() -> None:
    # A reverse-proxied gateway keeps its prefix; only the trailing /v1 is replaced.
    assert (
        _rerank_endpoint("https://proxy.example.com/gateway/v1")
        == "https://proxy.example.com/gateway/v2/rerank"
    )


# --------------------------------------------------------------------------- #
# FakeReranker
# --------------------------------------------------------------------------- #


def test_fake_reranker_orders_by_query_overlap() -> None:
    reranker = FakeReranker()
    documents = ["cats and gardens", "dog vaccine booster schedule", "dog leash"]
    results = reranker.rerank("dog vaccine schedule", documents, top_n=3)
    # "dog vaccine booster schedule" contains all three query tokens -> ranks first.
    assert results[0].index == 1
    assert results[0].relevance_score == pytest.approx(1.0)
    assert [result.index for result in results] == [1, 2, 0]


def test_fake_reranker_trims_to_top_n() -> None:
    results = FakeReranker().rerank("dog", ["dog a", "dog b", "cat c"], top_n=2)
    assert len(results) == 2


def test_fake_reranker_empty_documents_returns_empty() -> None:
    assert FakeReranker().rerank("dog", [], top_n=5) == []


def test_fake_reranker_ties_break_by_original_index() -> None:
    # No query tokens -> every score is 0.0, so order must stay stable by index.
    results = FakeReranker().rerank("", ["a", "b", "c"], top_n=3)
    assert [result.index for result in results] == [0, 1, 2]


# --------------------------------------------------------------------------- #
# CohereGatewayReranker
# --------------------------------------------------------------------------- #


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_cohere_reranker_sends_expected_request_and_parses_results() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 2, "relevance_score": 0.91},
                    {"index": 0, "relevance_score": 0.42},
                ]
            },
        )

    reranker = CohereGatewayReranker(_settings(), client=_mock_client(handler))
    results = reranker.rerank("is grass eating ok", ["a", "b", "c"], top_n=2)

    assert results == [
        RerankResult(index=2, relevance_score=0.91),
        RerankResult(index=0, relevance_score=0.42),
    ]
    assert captured["url"] == "https://ai-gateway.vercel.sh/v2/rerank"
    assert captured["auth"] == "Bearer test-key"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "cohere/rerank-v3.5"
    assert body["query"] == "is grass eating ok"
    assert body["documents"] == ["a", "b", "c"]
    assert body["top_n"] == 2


def test_cohere_reranker_caps_top_n_at_document_count() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 1.0}]})

    reranker = CohereGatewayReranker(_settings(), client=_mock_client(handler))
    reranker.rerank("q", ["only-one"], top_n=25)

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["top_n"] == 1


def test_cohere_reranker_empty_documents_makes_no_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("no request should be made for empty documents")

    reranker = CohereGatewayReranker(_settings(), client=_mock_client(handler))
    assert reranker.rerank("q", [], top_n=5) == []


def test_cohere_reranker_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    reranker = CohereGatewayReranker(_settings(), client=_mock_client(handler))
    with pytest.raises(httpx.HTTPStatusError):
        reranker.rerank("q", ["a"], top_n=1)


def test_cohere_reranker_builds_a_default_client_when_none_given() -> None:
    # The client=None branch constructs a real httpx.Client (no network on init).
    reranker = CohereGatewayReranker(_settings())
    assert isinstance(reranker._client, httpx.Client)
