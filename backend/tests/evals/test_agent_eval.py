"""Tests for the EvalAgent wrapper.

build_eval_agent wires live Qdrant + Gateway services, so it is covered by the
opt-in live eval, not here. These tests pin the wrapper's own logic (mode label,
answer delegation) with a scripted agent, and confirm rerank is now an accepted
mode after the Task 6 guard removal.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from app.agent.prompt import VET_DISCLAIMER
from app.agent.schemas import AgentAnswer
from evals.rag import agent_eval
from evals.rag.agent_eval import (
    EVAL_DOG_ID,
    EvalAgent,
    build_full_eval_agent,
    default_sleep_reader,
)
from tests.agent.conftest import build_test_agent, make_agent_settings


def test_eval_agent_defaults_to_dense_mode() -> None:
    agent = build_test_agent(responses=[AIMessage(content="x")])
    assert EvalAgent(agent).mode == "dense"


def test_build_eval_agent_threads_mode_into_retriever(monkeypatch: pytest.MonkeyPatch) -> None:
    # The removed Task 6 guard used to reject non-dense; build_eval_agent must now
    # thread the mode into build_retriever. Stub build_retriever to stay hermetic.
    recorded: dict[str, object] = {}

    def fake_build_retriever(*, mode: str = "dense") -> object:
        recorded["mode"] = mode
        return object()

    monkeypatch.setattr(agent_eval, "build_retriever", fake_build_retriever)
    eval_agent = agent_eval.build_eval_agent(settings=make_agent_settings(), mode="rerank")
    assert recorded["mode"] == "rerank"
    assert eval_agent.mode == "rerank"


async def test_eval_agent_answer_delegates_to_agent() -> None:
    agent = build_test_agent(
        responses=[AIMessage(content=f"Occasional grass is fine. {VET_DISCLAIMER}")]
    )
    eval_agent = EvalAgent(agent, mode="rerank")
    answer = await eval_agent.answer("Is grass-eating normal?")
    assert isinstance(answer, AgentAnswer)
    assert "Occasional grass is fine." in answer.text


# --------------------------------------------------------------------------- #
# PR A: the harness can now reach all nine tools
# --------------------------------------------------------------------------- #


def _memory_tool_call(call_id: str = "m1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "list_dog_memories", "args": {}, "id": call_id, "type": "tool_call"}],
    )


def _sleep_tool_call(call_id: str = "s1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_dog_sleep_summary",
                "args": {"days": 7},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def test_default_sleep_reader_reports_a_full_window() -> None:
    summary = default_sleep_reader()._summary
    assert summary.days_with_data == summary.days_requested
    assert summary.average_total_sleep_hours is not None


async def test_eval_agent_threads_dog_id_and_sleep_reader_to_reach_gated_tools() -> None:
    # With a memory store bound (with_memory) plus a dog_id and a sleep reader
    # threaded by EvalAgent, both a memory tool and a sleep tool become reachable
    # in one run -- the five tools the four-tool harness never exposed.
    agent = build_test_agent(
        responses=[
            _memory_tool_call(),
            _sleep_tool_call(),
            AIMessage(content=f"All noted. {VET_DISCLAIMER}"),
        ],
        with_memory=True,
    )
    eval_agent = EvalAgent(agent, dog_id=EVAL_DOG_ID, sleep_reader=default_sleep_reader())
    answer = await eval_agent.answer("What do you remember, and how did she sleep?")
    assert "list_dog_memories" in answer.tool_calls
    assert "get_dog_sleep_summary" in answer.tool_calls


def test_build_full_eval_agent_binds_the_memory_and_sleep_seams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_eval, "build_retriever", lambda *, mode="dense": object())
    eval_agent = build_full_eval_agent(settings=make_agent_settings())
    assert eval_agent.dog_id == EVAL_DOG_ID
    assert eval_agent.sleep_reader is not None


def test_build_eval_agent_stays_four_tools_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # The generation eval must keep its four-tool agent (no memory/sleep seams), or
    # the committed generation baselines silently move.
    monkeypatch.setattr(agent_eval, "build_retriever", lambda *, mode="dense": object())
    eval_agent = agent_eval.build_eval_agent(settings=make_agent_settings())
    assert eval_agent.dog_id is None
    assert eval_agent.sleep_reader is None
