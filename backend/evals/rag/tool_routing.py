"""Deterministic tool-routing eval: does the agent pick the right tool?

The agent exposes nine tools and, until now, nothing measured whether it selects
the right one for a question. This scores that directly and without a judge model,
over the ``AgentAnswer.tool_calls`` names the runner already returns -- no
production change, no LLM grading, so the number is reproducible and cheap.

Each golden case lists one or more *acceptable tool sets* (order-independent:
``get_current_date`` may legitimately precede a relative-date sleep query, so both
``{get_dog_sleep_summary}`` and ``{get_current_date, get_dog_sleep_summary}`` can be
correct). A case is correct when the set of tools actually invoked equals one of
them. On top of exact-set accuracy we report micro/macro precision-recall-F1 over
tool names (best-matching acceptable set per case), the rate at which
must-abstain questions wrongly called a tool, and mean calls per query.

We deliberately do NOT use RAGAS ToolCallAccuracy/F1 as the headline: that compares
tool *arguments* by exact match, which is undefined for the free-text query strings
our tools take (retrieve_vet_corpus, web_search, ...), so it would score structural
zeros. Name-level set scoring is the honest metric for this tool surface.

Run:
- make agent-routing-eval                       (spike: ARGS="--limit 10")
- make agent-routing-eval ARGS="--write-baseline"

Needs live Gateway + Qdrant (the real model decides which tool to call).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from app.agent.fakes import FakePetFood, FakeWebSearch
from app.agent.pet_food import PetFoodNutrient, PetFoodProduct
from app.agent.web_search import WebSearchResult
from app.rag.observability import configure_langsmith
from app.rag.schemas import RetrievalMode
from evals.rag.agent_eval import EvalAgent, build_full_eval_agent

DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "tool_golden.jsonl"
BASELINES_PATH = Path(__file__).resolve().parent / "baselines.json"


class ToolGoldenCase(BaseModel):
    """One question and the tool sets that count as correct routing for it."""

    model_config = ConfigDict(frozen=True)

    question: str
    bucket: str
    acceptable_tool_sets: tuple[frozenset[str], ...]
    must_call_none: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _normalize_abstention(self) -> ToolGoldenCase:
        # A must-abstain case is correct only when no tool ran, so the one
        # acceptable set is the empty set -- pin that rather than trusting the file.
        if self.must_call_none:
            object.__setattr__(self, "acceptable_tool_sets", (frozenset(),))
        return self


class ToolRoutingResult(BaseModel):
    """One case scored: what ran, whether it matched, and the best-match counts."""

    model_config = ConfigDict(frozen=True)

    question: str
    bucket: str
    invoked_tools: tuple[str, ...]
    matched_gold: tuple[str, ...]
    correct: bool
    true_positive: int
    false_positive: int
    false_negative: int


class ToolRoutingReport(BaseModel):
    """Aggregate routing quality across the golden set."""

    model_config = ConfigDict(frozen=True)

    total: int
    correct: int
    exact_set_accuracy: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    macro_f1: float
    per_tool_f1: dict[str, float]
    unnecessary_tool_rate: float | None
    mean_tool_calls_per_query: float
    accuracy_by_bucket: dict[str, float]
    results: tuple[ToolRoutingResult, ...]


def load_golden_cases(path: Path = DATASET_PATH) -> list[ToolGoldenCase]:
    """Load the tool-routing golden set from JSONL (one case per line)."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [ToolGoldenCase.model_validate_json(line) for line in lines]


def _f1(true_positive: int, false_positive: int, false_negative: int) -> float:
    denominator = 2 * true_positive + false_positive + false_negative
    # No predicted and no expected tools is a perfect match (the abstention case).
    return (2 * true_positive) / denominator if denominator else 1.0


def _best_match(
    predicted: frozenset[str], acceptable: tuple[frozenset[str], ...]
) -> tuple[frozenset[str], int, int, int]:
    """Pick the acceptable set that scores the prediction best, and its TP/FP/FN."""
    best: tuple[float, frozenset[str], int, int, int] | None = None
    for gold in acceptable:
        true_positive = len(predicted & gold)
        false_positive = len(predicted - gold)
        false_negative = len(gold - predicted)
        score = _f1(true_positive, false_positive, false_negative)
        if best is None or score > best[0]:
            best = (score, gold, true_positive, false_positive, false_negative)
    assert best is not None  # acceptable_tool_sets always has at least one set
    return best[1], best[2], best[3], best[4]


def score_case(case: ToolGoldenCase, invoked_tools: list[str]) -> ToolRoutingResult:
    """Score one case against its acceptable sets (order- and duplicate-independent)."""
    predicted = frozenset(invoked_tools)
    gold, true_positive, false_positive, false_negative = _best_match(
        predicted, case.acceptable_tool_sets
    )
    return ToolRoutingResult(
        question=case.question,
        bucket=case.bucket,
        invoked_tools=tuple(invoked_tools),
        matched_gold=tuple(sorted(gold)),
        correct=predicted in case.acceptable_tool_sets,
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
    )


def summarize(cases: list[ToolGoldenCase], results: list[ToolRoutingResult]) -> ToolRoutingReport:
    """Fold per-case results into micro/macro metrics and per-bucket accuracy."""
    total = len(results)
    total_true_positive = sum(result.true_positive for result in results)
    total_false_positive = sum(result.false_positive for result in results)
    total_false_negative = sum(result.false_negative for result in results)
    micro_precision = _ratio(total_true_positive, total_true_positive + total_false_positive)
    micro_recall = _ratio(total_true_positive, total_true_positive + total_false_negative)
    micro_f1 = _f1(total_true_positive, total_false_positive, total_false_negative)

    per_tool_f1 = _per_tool_f1(results)
    macro_f1 = sum(per_tool_f1.values()) / len(per_tool_f1) if per_tool_f1 else 1.0

    abstain_results = [
        result for case, result in zip(cases, results, strict=True) if case.must_call_none
    ]
    unnecessary_tool_rate = (
        sum(1 for result in abstain_results if result.invoked_tools) / len(abstain_results)
        if abstain_results
        else None
    )

    return ToolRoutingReport(
        total=total,
        correct=sum(1 for result in results if result.correct),
        exact_set_accuracy=_ratio(sum(1 for result in results if result.correct), total),
        micro_precision=micro_precision,
        micro_recall=micro_recall,
        micro_f1=micro_f1,
        macro_f1=macro_f1,
        per_tool_f1=per_tool_f1,
        unnecessary_tool_rate=unnecessary_tool_rate,
        mean_tool_calls_per_query=(
            sum(len(result.invoked_tools) for result in results) / total if total else 0.0
        ),
        accuracy_by_bucket=_accuracy_by_bucket(results),
        results=tuple(results),
    )


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _per_tool_f1(results: list[ToolRoutingResult]) -> dict[str, float]:
    """Per-tool F1 over every tool that appears in a prediction or a matched gold."""
    tools: set[str] = set()
    for result in results:
        tools.update(result.invoked_tools)
        tools.update(result.matched_gold)
    per_tool: dict[str, float] = {}
    for tool in sorted(tools):
        true_positive = false_positive = false_negative = 0
        for result in results:
            predicted = set(result.invoked_tools)
            gold = set(result.matched_gold)
            if tool in predicted and tool in gold:
                true_positive += 1
            elif tool in predicted:
                false_positive += 1
            elif tool in gold:
                false_negative += 1
        per_tool[tool] = _f1(true_positive, false_positive, false_negative)
    return per_tool


def _accuracy_by_bucket(results: list[ToolRoutingResult]) -> dict[str, float]:
    buckets: dict[str, list[ToolRoutingResult]] = {}
    for result in results:
        buckets.setdefault(result.bucket, []).append(result)
    return {
        bucket: _ratio(sum(1 for r in items if r.correct), len(items))
        for bucket, items in sorted(buckets.items())
    }


# The routing agent gets non-empty web/food fakes so a tool that is *chosen*
# returns something, and the model does not fall back to another tool on an empty
# result -- which would corrupt the very selection signal we measure.
def _routing_web_search() -> FakeWebSearch:
    return FakeWebSearch(
        [WebSearchResult(title="Update", url="https://news.example.com/x", content="An update.")]
    )


def _routing_pet_food() -> FakePetFood:
    return FakePetFood(
        [
            PetFoodProduct(
                code="0000000000000",
                name="Six Fish",
                brands="Orijen",
                quantity="2 kg",
                ingredients_text="Whole sardine, whole hake.",
                nutrients=[PetFoodNutrient(label="Crude protein", value=40.0)],
                url="https://world.openpetfoodfacts.org/product/0000000000000",
            )
        ]
    )


def build_routing_agent(mode: RetrievalMode = "dense") -> EvalAgent:
    """A full nine-tool eval agent wired for routing measurement."""
    return build_full_eval_agent(
        mode=mode, web_search=_routing_web_search(), pet_food=_routing_pet_food()
    )


async def run_tool_routing_eval(
    agent: EvalAgent, cases: list[ToolGoldenCase], *, concurrency: int = 4
) -> ToolRoutingReport:
    """Answer and score every case concurrently (bounded), preserving input order."""
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _score(case: ToolGoldenCase) -> ToolRoutingResult:
        async with semaphore:
            answer = await agent.answer(case.question)
            return score_case(case, list(answer.tool_calls))

    results = list(await asyncio.gather(*(_score(case) for case in cases)))
    return summarize(cases, results)


def render_lines(report: ToolRoutingReport) -> list[str]:
    """Human-readable summary, headed by exact-set accuracy and micro F1."""
    unnecessary = (
        f"{report.unnecessary_tool_rate:.2f}" if report.unnecessary_tool_rate is not None else "n/a"
    )
    lines = [
        f"Tool-routing eval: {report.correct}/{report.total} correct "
        f"(exact-set accuracy {report.exact_set_accuracy:.2f})",
        f"  micro P/R/F1: {report.micro_precision:.2f} / {report.micro_recall:.2f} / "
        f"{report.micro_f1:.2f}   macro F1: {report.macro_f1:.2f}",
        f"  unnecessary-tool rate (abstain cases): {unnecessary}   "
        f"mean calls/query: {report.mean_tool_calls_per_query:.2f}",
        "  accuracy by bucket: "
        + ", ".join(
            f"{bucket} {accuracy:.2f}" for bucket, accuracy in report.accuracy_by_bucket.items()
        ),
        "",
    ]
    for result in report.results:
        mark = "PASS" if result.correct else "FAIL"
        got = ", ".join(result.invoked_tools) or "(none)"
        lines.append(f"  [{mark}] {result.bucket}: {result.question}  ->  {got}")
    return lines


def write_routing_baseline(report: ToolRoutingReport, path: Path = BASELINES_PATH) -> None:
    """Persist under the ``routing`` key, merging so other sections survive.

    Refuses an empty set: a zero-case report would clobber a real baseline.
    """
    if report.total == 0:
        raise SystemExit("Refusing to write a routing baseline with no scored cases.")
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing["routing"] = report.model_dump()
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote routing baseline to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic tool-routing eval over the agent.")
    parser.add_argument(
        "--limit", type=int, default=None, help="score only the first N cases (spike)"
    )
    parser.add_argument("--concurrency", type=int, default=4, help="cases scored in parallel")
    parser.add_argument(
        "--mode", default="dense", choices=["dense", "rerank"], help="retriever mode"
    )
    parser.add_argument(
        "--write-baseline", action="store_true", help="persist the routing baseline"
    )
    args = parser.parse_args()

    configure_langsmith()
    cases = load_golden_cases()
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No routing cases to score.")

    agent = build_routing_agent(mode=args.mode)
    report = asyncio.run(run_tool_routing_eval(agent, cases, concurrency=args.concurrency))
    print("\n".join(render_lines(report)))
    if args.write_baseline:
        write_routing_baseline(report)


if __name__ == "__main__":
    main()
