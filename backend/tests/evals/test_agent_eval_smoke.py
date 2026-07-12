"""Opt-in live smoke for the agent generation eval.

Skipped unless RUN_AGENT_SMOKE=1 and the live dependencies are present
(Gateway key, Qdrant, an ingested corpus). Exercises the whole chain - context
capture, deterministic agent, and the four RAGAS metrics - over real dataset
cases, asserting the run does not crash and every metric is a valid float.

    RUN_AGENT_SMOKE=1 uv run --group evals pytest tests/evals/test_agent_eval_smoke.py
"""

from __future__ import annotations

import math
import os

import pytest

from evals.rag.agent_eval import build_eval_agent
from evals.rag.generation import load_generation_cases
from evals.rag.generation_metrics import GENERATION_METRIC_NAMES, build_generation_scorer
from evals.rag.run_agent_eval import run_eval

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_AGENT_SMOKE"),
    reason="live agent eval - set RUN_AGENT_SMOKE=1 with Gateway + Qdrant + ingested corpus",
)


async def test_agent_eval_smoke() -> None:
    agent = build_eval_agent(mode="dense")
    scorer = build_generation_scorer()

    # Step 1 live: a clearly grounded question should retrieve corpus passages.
    answer = await agent.answer("How often do adult dogs need a core vaccine booster?")
    assert answer.contexts, "a grounded corpus question should retrieve passages"

    # Steps 2-5 live: score real dataset cases; every metric is a valid float.
    cases = load_generation_cases()[:2]
    assert cases, "committed synthetic test set should not be empty"
    results = await run_eval(agent, scorer, cases)
    assert len(results) == len(cases)

    scored = [result.scores for result in results if result.scores is not None]
    assert scored, "at least one case should score (not all budget-exhausted)"
    for score in scored:
        for name in GENERATION_METRIC_NAMES:
            value = getattr(score, name)
            assert isinstance(value, float)
            assert math.isnan(value) or 0.0 <= value <= 1.0
