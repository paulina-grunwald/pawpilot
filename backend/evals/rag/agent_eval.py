"""Deterministic PawPilot agent for RAGAS generation evals."""

from __future__ import annotations

from app.agent.config import AgentSettings, get_agent_settings
from app.agent.fakes import FakePetFood, FakeWebSearch
from app.agent.graph import build_chat_model
from app.agent.pet_food import PetFoodLookup
from app.agent.runner import PawPilotAgent
from app.agent.schemas import AgentAnswer
from app.agent.web_search import WebSearch
from app.rag.retriever import build_retriever
from app.rag.schemas import RetrievalMode


def build_eval_settings(base: AgentSettings | None = None) -> AgentSettings:
    """Agent settings with temperature pinned to 0 for deterministic scoring."""
    resolved = base if base is not None else get_agent_settings()
    return resolved.model_copy(update={"agent_temperature": 0.0})


class EvalAgent:
    """A deterministic agent wrapper exposing a single answer coroutine.

    mode names the retriever configuration under evaluation; it labels the
    baseline and report (agent_ragas_<mode>.md) and is threaded into
    build_retriever so the agent answers over that retriever (Task 6 compares
    dense vs rerank this way).
    """

    def __init__(self, agent: PawPilotAgent, *, mode: RetrievalMode = "dense") -> None:
        self._agent = agent
        self._mode = mode

    @property
    def mode(self) -> RetrievalMode:
        return self._mode

    async def answer(self, question: str) -> AgentAnswer:
        """Answer one question with no thread or memory (single-shot, stateless)."""
        return await self._agent.arun(question)


def build_eval_agent(
    *,
    settings: AgentSettings | None = None,
    mode: RetrievalMode = "dense",
    web_search: WebSearch | None = None,
    pet_food: PetFoodLookup | None = None,
) -> EvalAgent:
    """Assemble the deterministic eval agent (real retriever, faked web + memory).

    mode selects the retriever configuration (dense or rerank) so the same
    harness scores either; hybrid stays unwired and the retriever rejects it.

    web_search / pet_food override the default empty fakes so an eval can feed the
    agent controlled tool output (for example the injection eval's poisoned web
    payloads); left unset, both are empty and the real model still decides whether
    to call the tool.
    """
    resolved = build_eval_settings(settings)
    agent = PawPilotAgent(
        model=build_chat_model(resolved),
        retriever=build_retriever(mode=mode),
        web_search=web_search if web_search is not None else FakeWebSearch([]),
        pet_food=pet_food if pet_food is not None else FakePetFood([]),
        settings=resolved,
        checkpointer=None,
        memory_store=None,
    )
    return EvalAgent(agent, mode=mode)
