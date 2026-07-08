"""RAGAS dense-baseline retrieval eval

Computes golden-set recall@k (deterministic) + RAGAS ContextRecall /
ContextEntityRecall over the synthetic test set, prints a report, and
optionally writes baselines.json. Phases 009b/009c re-run this and compare.

Run:  make rag-eval                    (installs the evals group, then runs this)
      make rag-eval ARGS=--write-baseline
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.rag.config import get_rag_settings
from app.rag.observability import configure_langsmith
from app.rag.retriever import VetCorpusRetriever, build_retriever
from evals.rag.golden import DEFAULT_KS, load_golden, recall_at_k
from evals.rag.judge import build_sync_judge_llm

SYNTHETIC_PATH = Path(__file__).resolve().parent / "datasets" / "synthetic_testset.jsonl"
BASELINES_PATH = Path(__file__).resolve().parent / "baselines.json"


def run_ragas_sync(func: Callable[[], Any]) -> Any:
    # RAGAS coroutines run off any ambient event loop, in a dedicated worker.
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(func).result()


def _mean(values: Sequence[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def evaluate_golden(
    retriever: VetCorpusRetriever, top_k: int = max(DEFAULT_KS)
) -> dict[str, float]:
    golden = load_golden()
    per_k: dict[int, list[float]] = {k: [] for k in DEFAULT_KS}
    for item in golden:
        retrieved = retriever.retrieve(item.query, top_k=top_k)
        for k in DEFAULT_KS:
            per_k[k].append(recall_at_k(item.expected_source_ids, retrieved, k))
    return {f"recall@{k}": round(sum(per_k[k]) / len(per_k[k]), 4) for k in DEFAULT_KS}


def _load_synthetic() -> list[dict[str, Any]]:
    if not SYNTHETIC_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in SYNTHETIC_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


async def _score_context_metrics(
    retriever: VetCorpusRetriever, rows: list[dict[str, Any]], judge: Any
) -> dict[str, float | None]:
    # Imported lazily so the module (and write_baseline) stays usable without the
    # optional evals dependency group installed.
    from ragas.metrics.collections import ContextEntityRecall, ContextRecall

    context_recall = ContextRecall(llm=judge)
    entity_recall = ContextEntityRecall(llm=judge)
    context_depth = get_rag_settings().default_top_k
    recall_scores: list[float] = []
    entity_scores: list[float] = []
    for row in rows:
        retrieved = retriever.retrieve(row["user_input"], top_k=context_depth)
        contexts = [chunk.text for chunk in retrieved]
        reference = row["reference"]
        recall = await context_recall.ascore(
            user_input=row["user_input"], retrieved_contexts=contexts, reference=reference
        )
        entity = await entity_recall.ascore(reference=reference, retrieved_contexts=contexts)
        recall_scores.append(recall.value)
        entity_scores.append(entity.value)
    return {
        "context_recall": _mean(recall_scores),
        "context_entity_recall": _mean(entity_scores),
        "cases": len(rows),
    }


def write_baseline(report: dict[str, Any], path: Path = BASELINES_PATH) -> None:
    """Persist the report as the retrieval baseline, refusing to clobber real metrics.

    A report with empty context metrics (the synthetic test set was absent) would
    overwrite the committed RAGAS numbers 009b/009c compare against — so refuse.
    """
    if not report["context"]:
        raise SystemExit(
            "Refusing to write baselines.json without synthetic context metrics — the "
            "synthetic test set is missing. Run `uv run python -m evals.rag.synth` first."
        )
    path.write_text(json.dumps({"retrieval": report}, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote dense baseline to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS dense-baseline retrieval eval.")
    parser.add_argument("--write-baseline", action="store_true", help="persist to baselines.json")
    args = parser.parse_args()

    configure_langsmith()
    retriever = build_retriever()

    golden = evaluate_golden(retriever)
    print("Golden set recall:")
    for name, value in golden.items():
        print(f"  {name}: {value}")

    synthetic = _load_synthetic()
    context: dict[str, float | None] = {}
    if synthetic:
        judge = build_sync_judge_llm()
        context = run_ragas_sync(
            lambda: asyncio.run(_score_context_metrics(retriever, synthetic, judge))
        )
        print("RAGAS context metrics (synthetic set):")
        for name, value in context.items():
            print(f"  {name}: {value}")
    else:
        print("No synthetic test set — run `uv run python -m evals.rag.synth` first.")

    report = {"mode": "dense", "golden": golden, "context": context}
    print("\n" + json.dumps(report, indent=2))
    if args.write_baseline:
        write_baseline(report)


if __name__ == "__main__":
    main()
