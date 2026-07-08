from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.rag.run_retrieval import write_baseline


def _report(context: dict[str, Any]) -> dict[str, Any]:
    return {"mode": "dense", "golden": {"recall@5": 0.5}, "context": context}


def test_write_baseline_refuses_without_context_metrics(tmp_path: Path) -> None:
    destination = tmp_path / "baselines.json"
    destination.write_text('{"retrieval": {"context": {"context_recall": 0.9}}}\n')

    with pytest.raises(SystemExit, match="synthetic test set is missing"):
        write_baseline(_report({}), destination)

    assert json.loads(destination.read_text())["retrieval"]["context"]["context_recall"] == 0.9


def test_write_baseline_persists_when_context_present(tmp_path: Path) -> None:
    destination = tmp_path / "baselines.json"
    write_baseline(_report({"context_recall": 0.8, "cases": 3}), destination)

    written = json.loads(destination.read_text())
    assert written["retrieval"]["context"]["context_recall"] == 0.8
    assert written["retrieval"]["mode"] == "dense"
