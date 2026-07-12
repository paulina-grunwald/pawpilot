"""Tests for the deterministic RAGAS eval agent builder.

These exercise the temperature-pinning helper, the EvalAgent wrapper (over a
scripted agent, so no keys or network), and the build_eval_agent mode guard.
The live wiring inside build_eval_agent is covered by the opt-in smoke test.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from app.agent.prompt import VET_DISCLAIMER
from app.agent.schemas import AgentAnswer
from app.rag.schemas import RetrievalMode
from evals.rag.agent_eval import EvalAgent, build_eval_agent, build_eval_settings
from tests.agent.conftest import (
    build_test_agent,
    make_agent_settings,
    make_chunk,
    tool_call_message,
)

# --------------------------------------------------------------------------- #
# build_eval_settings
# --------------------------------------------------------------------------- #


def test_build_eval_settings_pins_temperature_to_zero() -> None:
    pinned = build_eval_settings(make_agent_settings(agent_temperature=0.7))
    assert pinned.agent_temperature == 0.0


def test_build_eval_settings_preserves_other_fields() -> None:
    base = make_agent_settings(agent_temperature=0.7, agent_model="openai/gpt-5.4-mini")
    pinned = build_eval_settings(base)
    assert pinned.agent_model == "openai/gpt-5.4-mini"
    assert pinned.gateway_api_key.get_secret_value() == "test-gateway-key"


def test_build_eval_settings_does_not_mutate_base() -> None:
    base = make_agent_settings(agent_temperature=0.7)
    build_eval_settings(base)
    assert base.agent_temperature == 0.7


# --------------------------------------------------------------------------- #
# EvalAgent wrapper
# --------------------------------------------------------------------------- #


def test_eval_agent_mode_defaults_to_dense() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")])
    assert EvalAgent(agent).mode == "dense"


def test_eval_agent_exposes_given_mode() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")])
    assert EvalAgent(agent, mode="dense").mode == "dense"


async def test_eval_agent_answer_returns_agent_answer() -> None:
    agent = build_test_agent(responses=[AIMessage(content=f"Feed twice daily. {VET_DISCLAIMER}")])
    answer = await EvalAgent(agent).answer("How often should I feed my dog?")
    assert isinstance(answer, AgentAnswer)
    assert "Feed twice daily." in answer.text


async def test_eval_agent_answer_exposes_retrieved_contexts() -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "vaccine booster"),
            AIMessage(content=f"Boost every three years [S1]. {VET_DISCLAIMER}"),
        ],
        chunks=[make_chunk(text="Adult dogs need a core booster every three years.")],
    )
    answer = await EvalAgent(agent).answer("How often are boosters needed?")
    assert answer.contexts == ["Adult dogs need a core booster every three years."]


# --------------------------------------------------------------------------- #
# build_eval_agent - mode guard (raises before touching live services)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode", ["hybrid", "rerank"])
def test_build_eval_agent_rejects_non_dense_mode(mode: RetrievalMode) -> None:
    with pytest.raises(NotImplementedError, match="not wired until Task 6"):
        build_eval_agent(mode=mode)
