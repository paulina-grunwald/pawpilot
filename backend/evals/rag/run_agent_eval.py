"""Full RAGAS generation eval over the agent (dense baseline).

For each dataset case: run the deterministic eval agent, strip the emergency
banner, and score faithfulness / answer_accuracy / answer_relevancy /
noise_sensitivity against the judge.

Run:
- make agent-eval
- make agent-eval ARGS="--limit 3"
- make agent-eval ARGS="--write-baseline"   (persist baseline + report)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.agent.runner import _BUDGET_EXHAUSTED_MESSAGE as BUDGET_EXHAUSTED_MESSAGE
from app.rag.observability import configure_langsmith
from evals.rag.agent_eval import EvalAgent, build_eval_agent
from evals.rag.generation import GenerationCase, load_generation_cases
from evals.rag.generation_metrics import (
    GENERATION_METRIC_NAMES,
    GenerationSample,
    GenerationScorer,
    GenerationScores,
    build_generation_scorer,
    strip_boilerplate,
)
from evals.rag.run_retrieval import BASELINES_PATH, run_ragas_sync

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


class CaseResult(BaseModel):
    """One case's outcome: its flags and scores (None when budget-exhausted)."""

    model_config = ConfigDict(frozen=True)

    user_input: str
    emergency: bool
    budget_exhausted: bool
    scores: GenerationScores | None
    errored: bool = False


class GenerationReport(BaseModel):
    """The persisted summary for one mode: counts + per-metric means."""

    model_config = ConfigDict(frozen=True)

    mode: str
    total_cases: int
    scored_cases: int
    budget_exhausted: int
    errors: int
    emergency: int
    means: dict[str, float | None]


_DEFAULT_CONCURRENCY = 4


async def _run_case(agent: EvalAgent, scorer: GenerationScorer, case: GenerationCase) -> CaseResult:
    """Answer and score one case, isolating any failure to this case."""
    try:
        answer = await agent.answer(case.user_input)
    except Exception as error:  # one flaky agent run must not sink the whole eval
        print(f"  ! agent failed ({type(error).__name__}) for: {case.user_input[:70]!r}")
        return CaseResult(
            user_input=case.user_input,
            emergency=False,
            budget_exhausted=False,
            scores=None,
            errored=True,
        )
    response = strip_boilerplate(answer.text)
    if response == BUDGET_EXHAUSTED_MESSAGE:
        return CaseResult(
            user_input=case.user_input,
            emergency=answer.emergency,
            budget_exhausted=True,
            scores=None,
        )
    sample = GenerationSample(
        user_input=case.user_input,
        response=response,
        retrieved_contexts=answer.contexts,
        reference=case.reference,
    )
    try:
        scores = await scorer.ascore(sample)
    except Exception as error:  # one flaky judge call must not sink the whole run
        print(f"  ! scoring failed ({type(error).__name__}) for: {case.user_input[:70]!r}")
        return CaseResult(
            user_input=case.user_input,
            emergency=answer.emergency,
            budget_exhausted=False,
            scores=None,
            errored=True,
        )
    return CaseResult(
        user_input=case.user_input,
        emergency=answer.emergency,
        budget_exhausted=False,
        scores=scores,
    )


async def run_eval(
    agent: EvalAgent,
    scorer: GenerationScorer,
    cases: list[GenerationCase],
    *,
    concurrency: int = _DEFAULT_CONCURRENCY,
) -> list[CaseResult]:
    """Answer and score every case concurrently (bounded), preserving input order.

    Each case is I/O-bound (agent turns plus judge calls to the Gateway), so a
    small concurrency window cuts wall-clock sharply without raising credit cost.
    The semaphore caps in-flight cases to stay under Gateway rate limits, and
    _run_case never raises, so one bad case cannot cancel the others.
    """
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _bounded(case: GenerationCase) -> CaseResult:
        async with semaphore:
            return await _run_case(agent, scorer, case)

    return list(await asyncio.gather(*(_bounded(case) for case in cases)))


def aggregate_means(scores: list[GenerationScores]) -> dict[str, float | None]:
    """Per-metric mean over scored cases, skipping NaN values (None if all NaN)."""
    means: dict[str, float | None] = {}
    for name in GENERATION_METRIC_NAMES:
        finite = [value for score in scores if not math.isnan(value := getattr(score, name))]
        means[name] = round(sum(finite) / len(finite), 4) if finite else None
    return means


def summarize_report(mode: str, results: list[CaseResult]) -> GenerationReport:
    """Fold per-case results into the persisted summary for one mode."""
    scored = [result.scores for result in results if result.scores is not None]
    return GenerationReport(
        mode=mode,
        total_cases=len(results),
        scored_cases=len(scored),
        budget_exhausted=sum(1 for result in results if result.budget_exhausted),
        errors=sum(1 for result in results if result.errored),
        emergency=sum(1 for result in results if result.emergency),
        means=aggregate_means(scored),
    )


def _format_score(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def render_markdown(report: GenerationReport, results: list[CaseResult]) -> str:
    """Render the summary table, a per-case breakdown, and a conclusions stub."""
    labels = {"noise_sensitivity": "noise_sensitivity (lower better)"}
    lines = [
        f"# Agent RAGAS - {report.mode}",
        "",
        f"Cases: {report.total_cases} · scored: {report.scored_cases} · "
        f"budget-exhausted (excluded): {report.budget_exhausted} · "
        f"errored (excluded): {report.errors} · "
        f"emergency: {report.emergency}",
        "",
        "| metric | mean |",
        "|---|---|",
    ]
    for name in GENERATION_METRIC_NAMES:
        lines.append(f"| {labels.get(name, name)} | {_format_score(report.means[name])} |")

    metric_columns = " | ".join(GENERATION_METRIC_NAMES)
    metric_dividers = "|".join(["---"] * len(GENERATION_METRIC_NAMES))
    lines += [
        "",
        "## Per-case",
        "",
        f"| # | emergency | budget | error | {metric_columns} | question |",
        f"|---|---|---|---|{metric_dividers}|---|",
    ]
    for index, result in enumerate(results, start=1):
        cells = " | ".join(
            _format_score(getattr(result.scores, name, None)) for name in GENERATION_METRIC_NAMES
        )
        question = _truncate(result.user_input)
        emergency = "yes" if result.emergency else ""
        budget = "yes" if result.budget_exhausted else ""
        error = "yes" if result.errored else ""
        lines.append(f"| {index} | {emergency} | {budget} | {error} | {cells} | {question} |")

    lines += ["", "## Conclusions", "", "_TODO: interpret the numbers after review._", ""]
    return "\n".join(lines)


def _truncate(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def write_report(markdown: str, mode: str, reports_dir: Path = REPORTS_DIR) -> Path:
    """Write the markdown report to reports/agent_ragas_<mode>.md."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"agent_ragas_{mode}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def write_generation_baseline(report: GenerationReport, path: Path = BASELINES_PATH) -> None:
    """Persist the report under generation[mode], refusing to write empty means.

    Merges into any existing baselines.json so the retrieval section and other
    modes survive. A report with no scored cases (all means None) would clobber
    real numbers with nothing, so it is refused.
    """
    if all(value is None for value in report.means.values()):
        raise SystemExit(
            "Refusing to write generation baseline with no scored cases - every metric is "
            "empty (all cases were budget-exhausted or the dataset was empty)."
        )
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    generation = existing.get("generation", {})
    generation[report.mode] = report.model_dump()
    existing["generation"] = generation
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {report.mode} generation baseline to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Full RAGAS generation eval over the agent.")
    parser.add_argument(
        "--mode",
        default="dense",
        choices=["dense", "rerank"],
        help="retriever mode: dense (baseline) or rerank (Task 6)",
    )
    parser.add_argument("--limit", type=int, default=None, help="score only the first N cases")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=_DEFAULT_CONCURRENCY,
        help=f"cases scored in parallel (default {_DEFAULT_CONCURRENCY}); 1 is fully sequential",
    )
    parser.add_argument(
        "--write-baseline", action="store_true", help="persist baselines.json + the report"
    )
    args = parser.parse_args()

    configure_langsmith()
    cases = load_generation_cases()
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit(
            "No reviewed generation cases. Curate generation_golden.jsonl "
            "(uv run python -m evals.rag.curate), review each reference, and set reviewed=true."
        )

    agent = build_eval_agent(mode=args.mode)
    scorer = build_generation_scorer()
    results = run_ragas_sync(
        lambda: asyncio.run(run_eval(agent, scorer, cases, concurrency=args.concurrency))
    )
    report = summarize_report(args.mode, results)

    print(f"Agent RAGAS ({args.mode}) over {report.total_cases} cases:")
    print(json.dumps(report.model_dump(), indent=2))

    if args.write_baseline:
        write_report(render_markdown(report, results), args.mode)
        write_generation_baseline(report)


if __name__ == "__main__":
    main()
