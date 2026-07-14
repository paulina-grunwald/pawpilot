"""Golden-set retrieval eval (dense baseline or rerank).

Computes golden-set recall@k (deterministic) + RAGAS ContextRecall /
ContextEntityRecall over the reviewed generation golden set, prints a report,
and optionally writes baselines.json. Pass --mode rerank to score the advanced
retriever and compare its recall against the dense baseline (Task 6).

Run:  make rag-eval                          (dense; installs the evals group)
      make rag-eval ARGS="--mode rerank"     (advanced retriever)
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
from evals.rag.generation import load_generation_cases
from evals.rag.golden import DEFAULT_KS, load_golden, recall_at_k

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


def _load_context_cases() -> list[dict[str, Any]]:
    """Reviewed generation golden rows as the {user_input, reference} the context
    metrics need. Shares the curated set with the generation eval so both score the
    same owner questions, never the old contaminated synthetic set.
    """
    return [
        {"user_input": case.user_input, "reference": case.reference}
        for case in load_generation_cases()
    ]


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

    A report with empty context metrics (no reviewed generation cases) would
    overwrite the committed RAGAS numbers later phases compare against, so refuse.
    Merges into any existing baselines.json so the generation section (and any other
    keys) survive, rather than replacing the whole file with only the retrieval block.
    """
    if not report["context"]:
        raise SystemExit(
            "Refusing to write baselines.json without context metrics: there are no "
            "reviewed generation cases. Curate and review generation_golden.jsonl first "
            "(uv run python -m evals.rag.curate)."
        )
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing["retrieval"] = report
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {report['mode']} retrieval baseline to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Golden-set retrieval eval (dense or rerank).")
    parser.add_argument(
        "--mode",
        default="dense",
        choices=["dense", "rerank"],
        help="retriever mode: dense (baseline) or rerank (Task 6)",
    )
    parser.add_argument("--write-baseline", action="store_true", help="persist to baselines.json")
    args = parser.parse_args()

    configure_langsmith()
    retriever = build_retriever(mode=args.mode)

    golden = evaluate_golden(retriever)
    print("Golden set recall:")
    for name, value in golden.items():
        print(f"  {name}: {value}")

    cases = _load_context_cases()
    context: dict[str, float | None] = {}
    if cases:
        from evals.rag.judge import build_sync_judge_llm

        judge = build_sync_judge_llm()
        context = run_ragas_sync(
            lambda: asyncio.run(_score_context_metrics(retriever, cases, judge))
        )
        print("RAGAS context metrics (reviewed generation set):")
        for name, value in context.items():
            print(f"  {name}: {value}")
    else:
        print(
            "No reviewed generation cases — curate + review generation_golden.jsonl first "
            "(uv run python -m evals.rag.curate)."
        )

    report = {"mode": args.mode, "golden": golden, "context": context}
    print("\n" + json.dumps(report, indent=2))
    if args.write_baseline:
        write_baseline(report)


if __name__ == "__main__":
    main()
