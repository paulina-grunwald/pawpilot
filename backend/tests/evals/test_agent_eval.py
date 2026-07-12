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
from evals.rag.agent_eval import EvalAgent
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
