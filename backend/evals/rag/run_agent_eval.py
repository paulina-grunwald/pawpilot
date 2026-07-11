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
    strip_emergency_banner,
)
from evals.rag.run_retrieval import BASELINES_PATH, run_ragas_sync

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


class CaseResult(BaseModel):
    """One case's outcome: its flags and scores (``None`` when budget-exhausted)."""

    model_config = ConfigDict(frozen=True)

    user_input: str
    emergency: bool
    budget_exhausted: bool
    scores: GenerationScores | None


class GenerationReport(BaseModel):
    """The persisted summary for one mode: counts + per-metric means."""

    model_config = ConfigDict(frozen=True)

    mode: str
    total_cases: int
    scored_cases: int
    budget_exhausted: int
    emergency: int
    means: dict[str, float | None]


async def run_eval(
    agent: EvalAgent, scorer: GenerationScorer, cases: list[GenerationCase]
) -> list[CaseResult]:
    """Run and score every case, skipping the metric pass for canned answers."""
    results: list[CaseResult] = []
    for case in cases:
        answer = await agent.answer(case.user_input)
        response = strip_emergency_banner(answer.text)
        if response == BUDGET_EXHAUSTED_MESSAGE:
            results.append(
                CaseResult(
                    user_input=case.user_input,
                    emergency=answer.emergency,
                    budget_exhausted=True,
                    scores=None,
                )
            )
            continue
        sample = GenerationSample(
            user_input=case.user_input,
            response=response,
            retrieved_contexts=answer.contexts,
            reference=case.reference,
        )
        results.append(
            CaseResult(
                user_input=case.user_input,
                emergency=answer.emergency,
                budget_exhausted=False,
                scores=await scorer.ascore(sample),
            )
        )
    return results


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
        emergency=sum(1 for result in results if result.emergency),
        means=aggregate_means(scored),
    )


def _format_score(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def render_markdown(report: GenerationReport, results: list[CaseResult]) -> str:
    """Render the summary table, a per-case breakdown, and a conclusions stub."""
    labels = {"noise_sensitivity": "noise_sensitivity (lower better)"}
    lines = [
        f"# Agent RAGAS — {report.mode}",
        "",
        f"Cases: {report.total_cases} · scored: {report.scored_cases} · "
        f"budget-exhausted (excluded): {report.budget_exhausted} · "
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
        f"| # | emergency | budget | {metric_columns} | question |",
        f"|---|---|---|{metric_dividers}|---|",
    ]
    for index, result in enumerate(results, start=1):
        cells = " | ".join(
            _format_score(getattr(result.scores, name, None)) for name in GENERATION_METRIC_NAMES
        )
        question = _truncate(result.user_input)
        emergency = "yes" if result.emergency else ""
        budget = "yes" if result.budget_exhausted else ""
        lines.append(f"| {index} | {emergency} | {budget} | {cells} | {question} |")

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

    Merges into any existing baselines.json so the ``retrieval`` section and other
    modes survive. A report with no scored cases (all means ``None``) would clobber
    real numbers with nothing, so it is refused.
    """
    if all(value is None for value in report.means.values()):
        raise SystemExit(
            "Refusing to write generation baseline with no scored cases — every metric is "
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
    parser.add_argument("--mode", default="dense", help="retriever mode label (Task 5: dense)")
    parser.add_argument("--limit", type=int, default=None, help="score only the first N cases")
    parser.add_argument(
        "--write-baseline", action="store_true", help="persist baselines.json + the report"
    )
    args = parser.parse_args()

    configure_langsmith()
    cases = load_generation_cases()
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No generation cases — run `uv run python -m evals.rag.synth` first.")

    agent = build_eval_agent(mode=args.mode)
    scorer = build_generation_scorer()
    results = run_ragas_sync(lambda: asyncio.run(run_eval(agent, scorer, cases)))
    report = summarize_report(args.mode, results)

    print(f"Agent RAGAS ({args.mode}) over {report.total_cases} cases:")
    print(json.dumps(report.model_dump(), indent=2))

    if args.write_baseline:
        write_report(render_markdown(report, results), args.mode)
        write_generation_baseline(report)


if __name__ == "__main__":
    main()
