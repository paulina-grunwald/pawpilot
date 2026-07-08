"""Golden-set retrieval scoring (deterministic, no RAGAS).

Shared by the live ``scripts/retrieval_report`` and the RAGAS runner so there's
one definition of recall@k. ``recall_at_k`` is a per-query hit-rate (1.0 if any
expected source appears in the top-k, else 0.0); the mean over queries is
recall@k for the set.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from app.rag.schemas import RetrievedChunk

GOLDEN_PATH = Path(__file__).resolve().parent / "datasets" / "retrieval_golden.json"
DEFAULT_KS: tuple[int, ...] = (5, 8, 10, 20)


class GoldenQuery(BaseModel):
    query: str
    expected_source_ids: list[str]
    note: str | None = None


def load_golden(path: Path | None = None) -> list[GoldenQuery]:
    rows = json.loads((path or GOLDEN_PATH).read_text(encoding="utf-8"))
    return [GoldenQuery.model_validate(row) for row in rows]


def recall_at_k(expected_source_ids: list[str], retrieved: list[RetrievedChunk], k: int) -> float:
    expected = set(expected_source_ids)
    return 1.0 if any(chunk.source_id in expected for chunk in retrieved[:k]) else 0.0
