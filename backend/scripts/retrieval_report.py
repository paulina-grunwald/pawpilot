"""Live golden-set recall@k report (no RAGAS, no judge LLM).

Runs the real retriever over the golden set and prints per-query hits + aggregate
recall@k. Needs VERCEL_AI_GATEWAY + QDRANT_URL and an ingested corpus.

Run:  make retrieval-report
"""

from __future__ import annotations

from app.rag.observability import configure_langsmith
from app.rag.retriever import build_retriever
from evals.rag.golden import DEFAULT_KS, load_golden, recall_at_k


def main() -> None:
    configure_langsmith()
    retriever = build_retriever()
    golden = load_golden()
    totals = dict.fromkeys(DEFAULT_KS, 0.0)

    print(f"Golden-set retrieval report ({len(golden)} queries)\n")
    for item in golden:
        retrieved = retriever.retrieve(item.query, top_k=max(DEFAULT_KS))
        recalls = {k: recall_at_k(item.expected_source_ids, retrieved, k) for k in DEFAULT_KS}
        for k in DEFAULT_KS:
            totals[k] += recalls[k]
        marker = "HIT " if recalls[10] else "MISS"
        print(f"[{marker}] {item.query[:72]}")

    print("\nAggregate:")
    for k in DEFAULT_KS:
        print(f"  recall@{k}: {totals[k] / len(golden):.3f}")


if __name__ == "__main__":
    main()
