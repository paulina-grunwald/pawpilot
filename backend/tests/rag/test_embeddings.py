from __future__ import annotations

import math

from app.rag.embeddings import FakeEmbedder


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
