"""Push the RAGAS evals to LangSmith as Datasets and Experiments.

Run:
- make langsmith-experiments
- make langsmith-experiments ARGS="--kind generation --limit 5"
"""

from __future__ import annotations

import argparse
import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any

from app.agent.runner import _BUDGET_EXHAUSTED_MESSAGE as BUDGET_EXHAUSTED_MESSAGE
from app.rag.observability import configure_langsmith, tracing_enabled
from app.rag.retriever import VetCorpusRetriever, build_retriever
from evals.rag.agent_eval import EvalAgent, build_eval_agent
from evals.rag.generation import GenerationCase, load_generation_cases
from evals.rag.generation_metrics import (
    GENERATION_METRIC_NAMES,
    GenerationSample,
    GenerationScorer,
    build_generation_scorer,
    strip_boilerplate,
)
from evals.rag.golden import DEFAULT_KS, GoldenQuery, load_golden

GENERATION_DATASET = "pawpilot-generation-golden"
RETRIEVAL_DATASET = "pawpilot-retrieval-golden"

# run/example are LangSmith Run/Example objects; the adapters only read their
# .inputs/.outputs dicts, so they are typed loosely and driven with fakes in tests.
Evaluator = Callable[[Any, Any], Awaitable[dict[str, Any]]]


class LangSmithCredentialsError(SystemExit):
    """Raised when an experiment is requested without live LangSmith credentials."""


def require_langsmith() -> None:
    """Fail early and clearly when tracing or the API key is not configured."""
    if not tracing_enabled():
        raise LangSmithCredentialsError(
            "LangSmith experiments need LANGSMITH_TRACING=true; set it (and LANGSMITH_API_KEY) "
            "before running. See app/rag/observability.py."
        )
    if not os.environ.get("LANGSMITH_API_KEY"):
        raise LangSmithCredentialsError(
            "LANGSMITH_API_KEY is not set; experiments cannot upload to LangSmith."
        )


# Dataset example builders
def generation_examples(cases: list[GenerationCase]) -> list[dict[str, Any]]:
    """Map reviewed generation cases to LangSmith example dicts."""
    return [
        {"inputs": {"user_input": case.user_input}, "outputs": {"reference": case.reference}}
        for case in cases
    ]


def retrieval_examples(golden: list[GoldenQuery]) -> list[dict[str, Any]]:
    """Map retrieval golden queries to LangSmith example dicts."""
    return [
        {
            "inputs": {"query": item.query},
            "outputs": {"expected_source_ids": item.expected_source_ids},
        }
        for item in golden
    ]


# --------------------------------------------------------------------------- #
# Generation experiment
# --------------------------------------------------------------------------- #


async def generation_target(agent: EvalAgent, inputs: dict[str, Any]) -> dict[str, Any]:
    """Answer one dataset row with the eval agent (the aevaluate target)."""
    answer = await agent.answer(inputs["user_input"])
    response = strip_boilerplate(answer.text)
    return {
        "response": response,
        "retrieved_contexts": answer.contexts,
        "emergency": answer.emergency,
        "budget_exhausted": response == BUDGET_EXHAUSTED_MESSAGE,
    }


def make_generation_evaluator(scorer: GenerationScorer) -> Evaluator:
    """Build an async evaluator that scores one row across the four RAGAS metrics.

    Reuses GenerationScorer so LangSmith and the local eval score identically, and
    returns one feedback key per metric. Budget-exhausted rows (a canned answer)
    are skipped, mirroring run_eval.
    """

    async def evaluate(run: Any, example: Any) -> dict[str, Any]:
        outputs = run.outputs or {}
        if outputs.get("budget_exhausted"):
            return {"results": []}
        sample = GenerationSample(
            user_input=example.inputs["user_input"],
            response=outputs["response"],
            retrieved_contexts=outputs.get("retrieved_contexts", []),
            reference=(example.outputs or {})["reference"],
        )
        scores = await scorer.ascore(sample)
        return {
            "results": [
                {"key": name, "score": getattr(scores, name)} for name in GENERATION_METRIC_NAMES
            ]
        }

    return evaluate


async def run_generation_experiment(*, mode: str = "dense", limit: int | None = None) -> Any:
    """Sync the generation dataset and run the agent as a LangSmith experiment."""
    require_langsmith()
    from langsmith import Client, aevaluate

    cases = load_generation_cases()
    if limit is not None:
        cases = cases[:limit]
    if not cases:
        raise LangSmithCredentialsError(
            "No reviewed generation cases; curate generation_golden.jsonl first "
            "(uv run python -m evals.rag.curate)."
        )
    client = Client()
    sync_dataset(
        client,
        GENERATION_DATASET,
        generation_examples(cases),
        "PawPilot reviewed generation golden set: owner questions and reference answers.",
    )
    agent = build_eval_agent(mode=mode)  # already returns an EvalAgent; do not re-wrap
    evaluator = make_generation_evaluator(build_generation_scorer())

    async def target(inputs: dict[str, Any]) -> dict[str, Any]:
        return await generation_target(agent, inputs)

    return await aevaluate(
        target,
        data=GENERATION_DATASET,
        evaluators=[evaluator],
        experiment_prefix=f"pawpilot-generation-{mode}",
        client=client,
    )



# Retrieval experiment
def recall_at_k_by_ids(
    expected_source_ids: list[str], retrieved_source_ids: list[str], k: int
) -> float:
    """Per-query hit-rate: 1.0 if any expected source appears in the top-k retrieved ids."""
    expected = set(expected_source_ids)
    return 1.0 if any(source_id in expected for source_id in retrieved_source_ids[:k]) else 0.0


def retrieval_target(retriever: VetCorpusRetriever, inputs: dict[str, Any]) -> dict[str, Any]:
    """Retrieve for one query and return the ordered source ids (the aevaluate target)."""
    retrieved = retriever.retrieve(inputs["query"], top_k=max(DEFAULT_KS))
    return {"retrieved_source_ids": [chunk.source_id for chunk in retrieved]}


def recall_evaluator(run: Any, example: Any) -> dict[str, Any]:
    """Score recall@k for every k in DEFAULT_KS from the retrieved source ids."""
    retrieved_ids = (run.outputs or {}).get("retrieved_source_ids", [])
    expected = (example.outputs or {}).get("expected_source_ids", [])
    return {
        "results": [
            {"key": f"recall@{k}", "score": recall_at_k_by_ids(expected, retrieved_ids, k)}
            for k in DEFAULT_KS
        ]
    }


async def run_retrieval_experiment(*, mode: str = "dense", limit: int | None = None) -> Any:
    """Sync the retrieval dataset and run the retriever as a LangSmith experiment."""
    require_langsmith()
    from langsmith import Client, aevaluate

    golden = load_golden()
    if limit is not None:
        golden = golden[:limit]
    client = Client()
    sync_dataset(
        client,
        RETRIEVAL_DATASET,
        retrieval_examples(golden),
        "PawPilot retrieval golden set: queries and their expected source ids.",
    )
    retriever = build_retriever()

    async def target(inputs: dict[str, Any]) -> dict[str, Any]:
        return retrieval_target(retriever, inputs)

    return await aevaluate(
        target,
        data=RETRIEVAL_DATASET,
        evaluators=[recall_evaluator],
        experiment_prefix=f"pawpilot-retrieval-{mode}",
        client=client,
    )

# Dataset sync + entrypoint

def sync_dataset(client: Any, name: str, examples: list[dict[str, Any]], description: str) -> None:
    """Create the dataset with these examples if it does not exist yet (idempotent).

    Re-running keeps the existing dataset so experiments compare against one
    versioned set, rather than appending duplicate examples each run.
    """
    if client.has_dataset(dataset_name=name):
        return
    dataset = client.create_dataset(dataset_name=name, description=description)
    client.create_examples(dataset_id=dataset.id, examples=examples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RAGAS evals as LangSmith experiments.")
    parser.add_argument("--kind", choices=["generation", "retrieval", "both"], default="both")
    parser.add_argument(
        "--mode", default="dense", choices=["dense", "rerank"], help="retriever mode"
    )
    parser.add_argument("--limit", type=int, default=None, help="only the first N cases")
    args = parser.parse_args()

    # Promote LANGSMITH_* from .env into the environment (endpoint, project, key) so
    # the LangSmith client authenticates, then fail fast if creds are still missing.
    configure_langsmith()
    require_langsmith()
    if args.kind in ("generation", "both"):
        print("Running generation experiment...")
        print(asyncio.run(run_generation_experiment(mode=args.mode, limit=args.limit)))
    if args.kind in ("retrieval", "both"):
        print("Running retrieval experiment...")
        print(asyncio.run(run_retrieval_experiment(mode=args.mode, limit=args.limit)))


if __name__ == "__main__":
    main()
