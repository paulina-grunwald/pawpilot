from __future__ import annotations

import math
from types import SimpleNamespace

from app.rag.config import RagSettings
from app.rag.embeddings import FakeEmbedder, GatewayEmbedder


def test_fake_embedder_is_deterministic() -> None:
    embedder = FakeEmbedder(dimensions=16)
    assert embedder.embed_query("chocolate toxicity") == embedder.embed_query("chocolate toxicity")


def test_fake_embedder_distinguishes_texts() -> None:
    embedder = FakeEmbedder()
    assert embedder.embed_query("alpha") != embedder.embed_query("beta")


def test_fake_embedder_dimensions_and_unit_norm() -> None:
    embedder = FakeEmbedder(dimensions=12)
    vector = embedder.embed_query("vaccination schedule")
    assert len(vector) == 12
    assert embedder.dimensions == 12
    norm = math.sqrt(sum(value * value for value in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-9)


def test_fake_embedder_batch_and_empty() -> None:
    embedder = FakeEmbedder(dimensions=8)
    vectors = embedder.embed_documents(["x", "y", "z"])
    assert len(vectors) == 3
    assert all(len(vector) == 8 for vector in vectors)
    assert embedder.embed_documents([]) == []


def test_gateway_embedder_reorders_response_by_index() -> None:
    embedder = GatewayEmbedder(RagSettings(gateway_api_key="test-key"))
    # The Gateway may return items out of input order; each carries its index.
    shuffled = SimpleNamespace(
        data=[
            SimpleNamespace(index=2, embedding=[0.2]),
            SimpleNamespace(index=0, embedding=[0.0]),
            SimpleNamespace(index=1, embedding=[0.1]),
        ]
    )
    embedder._client = SimpleNamespace(  # type: ignore[assignment]
        embeddings=SimpleNamespace(create=lambda model, input: shuffled)
    )

    assert embedder.embed_documents(["a", "b", "c"]) == [[0.0], [0.1], [0.2]]
