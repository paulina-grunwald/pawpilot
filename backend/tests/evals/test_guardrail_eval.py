"""Tests for the scope-guardrail eval scoring logic.

run_guardrail_eval drives the live agent, so the live pass/fail lives in the
opt-in make target. These tests pin the deterministic pieces (refusal detection,
per-case scoring, aggregation, rendering) with hand-built answers, plus one async
run over a scripted agent.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agent.prompt import OFF_TOPIC_MESSAGE
from app.agent.red_flags import EMERGENCY_BANNER
from app.agent.schemas import AgentAnswer, Citation
from evals.rag.agent_eval import EvalAgent
from evals.rag.guardrail_eval import (
    GUARDRAIL_CASES,
    GuardrailCase,
    GuardrailResult,
    evaluate_case,
    is_refusal,
    render_lines,
    run_guardrail_eval,
    summarize,
)
from tests.agent.conftest import build_test_agent


def _answer(
    text: str, *, tool_calls: list[str] | None = None, citations: list[Citation] | None = None
) -> AgentAnswer:
    return AgentAnswer(
        text=text,
        citations=citations or [],
        emergency=False,
        tool_calls=tool_calls or [],
    )


def _citation() -> Citation:
    return Citation(ref="S1", kind="corpus", title="Source", url="https://example.test")


def test_fingerprint_matches_the_current_off_topic_message() -> None:
    assert is_refusal(OFF_TOPIC_MESSAGE)


def test_is_refusal_survives_emergency_banner_prefix() -> None:
    assert is_refusal(EMERGENCY_BANNER + OFF_TOPIC_MESSAGE)


def test_is_refusal_is_case_and_whitespace_insensitive() -> None:
    assert is_refusal(f"  {OFF_TOPIC_MESSAGE.upper()}\n")


def test_is_refusal_false_for_an_ordinary_answer() -> None:
    assert not is_refusal("Occasional grass-eating is usually normal.")


def test_evaluate_refusal_case_passes_when_clean() -> None:
    result = evaluate_case(
        GuardrailCase(question="q", expect_refusal=True), _answer(OFF_TOPIC_MESSAGE)
    )
    assert result.passed
    assert result.was_refused


def test_evaluate_refusal_case_fails_when_a_tool_ran() -> None:
    result = evaluate_case(
        GuardrailCase(question="q", expect_refusal=True),
        _answer(OFF_TOPIC_MESSAGE, tool_calls=["web_search"]),
    )
    assert not result.passed
    assert result.tool_calls == 1


def test_evaluate_refusal_case_fails_when_a_citation_leaked() -> None:
    result = evaluate_case(
        GuardrailCase(question="q", expect_refusal=True),
        _answer(OFF_TOPIC_MESSAGE, citations=[_citation()]),
    )
    assert not result.passed
    assert result.citations == 1


def test_evaluate_refusal_case_fails_when_the_question_was_answered() -> None:
    result = evaluate_case(
        GuardrailCase(question="q", expect_refusal=True), _answer("Sure, here you go.")
    )
    assert not result.passed
    assert not result.was_refused


def test_evaluate_in_scope_case_passes_when_answered() -> None:
    result = evaluate_case(
        GuardrailCase(question="q", expect_refusal=False), _answer("Grass-eating is fine.")
    )
    assert result.passed


def test_evaluate_in_scope_case_fails_when_refused() -> None:
    result = evaluate_case(
        GuardrailCase(question="q", expect_refusal=False), _answer(OFF_TOPIC_MESSAGE)
    )
    assert not result.passed


def _result(*, expect_refusal: bool, was_refused: bool, passed: bool) -> GuardrailResult:
    return GuardrailResult(
        question="q",
        expect_refusal=expect_refusal,
        was_refused=was_refused,
        tool_calls=0,
        citations=0,
        passed=passed,
    )


def test_summarize_counts_each_bucket() -> None:
    report = summarize(
        [
            _result(expect_refusal=True, was_refused=True, passed=True),
            _result(expect_refusal=True, was_refused=False, passed=False),
            _result(expect_refusal=False, was_refused=False, passed=True),
        ]
    )
    assert report.total == 3
    assert report.passed == 2
    assert (report.off_topic_refused, report.off_topic_total) == (1, 2)
    assert (report.in_scope_answered, report.in_scope_total) == (1, 1)


def test_render_lines_has_a_header_and_one_line_per_case() -> None:
    report = summarize(
        [
            _result(expect_refusal=True, was_refused=True, passed=True),
            _result(expect_refusal=False, was_refused=True, passed=False),
        ]
    )
    lines = render_lines(report)
    assert "1/2 passed" in lines[0]
    body = [line for line in lines if line.strip().startswith("[")]
    assert len(body) == 2
    assert body[0].strip().startswith("[PASS]")
    assert body[1].strip().startswith("[FAIL]")


def test_guardrail_cases_split_into_both_buckets() -> None:
    assert any(case.expect_refusal for case in GUARDRAIL_CASES)
    assert any(not case.expect_refusal for case in GUARDRAIL_CASES)


async def test_run_guardrail_eval_scores_a_scripted_refusal() -> None:
    agent = EvalAgent(build_test_agent(responses=[AIMessage(content=OFF_TOPIC_MESSAGE)]))
    report = await run_guardrail_eval(
        agent,
        cases=(GuardrailCase(question="What's the weather?", expect_refusal=True),),
        concurrency=1,
    )
    assert report.total == 1
    assert report.passed == 1
    assert report.off_topic_refused == 1
