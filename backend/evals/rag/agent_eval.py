"""Deterministic PawPilot agent for the RAGAS generation and tool-routing evals.

Two builders live here. ``build_eval_agent`` is the low-level one: by default it
binds only the four always-available tools (corpus, web, pet-food, clock), which is
what the generation eval scores and what every committed generation baseline was
produced under -- do not change that default or those numbers silently move.
``build_full_eval_agent`` binds all nine tools (adding the three memory tools and
the two sleep tools) by supplying a fixture ``dog_id``, an in-memory long-term
store, and a fake sleep reader, so the tool-routing eval can measure selection
across the whole surface the deployed agent actually exposes.
"""

from __future__ import annotations

from datetime import date

from langgraph.store.memory import InMemoryStore

from app.agent.config import AgentSettings, get_agent_settings
from app.agent.data_tools import SleepDataReader
from app.agent.fakes import FakePetFood, FakeSleepReader, FakeWebSearch
from app.agent.graph import build_chat_model
from app.agent.memory import DogMemoryStore
from app.agent.pet_food import PetFoodLookup
from app.agent.runner import PawPilotAgent
from app.agent.schemas import AgentAnswer
from app.agent.web_search import WebSearch
from app.integrations.tractive.read_service import SleepSummary
from app.rag.retriever import build_retriever
from app.rag.schemas import RetrievalMode

# A stable fixture dog id: binding a dog_id (with a memory store) is what activates
# the three memory tools, and it namespaces the in-memory store for a run.
EVAL_DOG_ID = "eval-dog"


def build_eval_settings(base: AgentSettings | None = None) -> AgentSettings:
    """Agent settings with temperature pinned to 0 for deterministic scoring."""
    resolved = base if base is not None else get_agent_settings()
    return resolved.model_copy(update={"agent_temperature": 0.0})


def default_sleep_reader() -> FakeSleepReader:
    """A fake sleep reader with a plausible preset summary (content is irrelevant
    to tool *selection*; the point is that the two sleep tools become bound)."""
    return FakeSleepReader(
        SleepSummary(
            days_requested=7,
            days_with_data=7,
            average_total_sleep_hours=12.5,
            average_night_sleep_hours=9.0,
            average_day_sleep_hours=3.5,
            start_date=date(2026, 5, 17),
            end_date=date(2026, 5, 23),
        )
    )


class EvalAgent:
    """A deterministic agent wrapper exposing a single answer coroutine.

    mode names the retriever configuration under evaluation; it labels the
    baseline and report (agent_ragas_<mode>.md) and is threaded into
    build_retriever so the agent answers over that retriever (Task 6 compares
    dense vs rerank this way).

    dog_id and sleep_reader are threaded into every ``arun`` so the memory and
    sleep tools are reachable when the underlying agent was built with them; left
    None (the generation-eval default) the run stays single-shot and stateless.
    """

    def __init__(
        self,
        agent: PawPilotAgent,
        *,
        mode: RetrievalMode = "dense",
        dog_id: str | None = None,
        sleep_reader: SleepDataReader | None = None,
    ) -> None:
        self._agent = agent
        self._mode = mode
        self._dog_id = dog_id
        self._sleep_reader = sleep_reader

    @property
    def mode(self) -> RetrievalMode:
        return self._mode

    @property
    def dog_id(self) -> str | None:
        return self._dog_id

    @property
    def sleep_reader(self) -> SleepDataReader | None:
        return self._sleep_reader

    async def answer(self, question: str) -> AgentAnswer:
        """Answer one question (single-shot: no thread, so no cross-question state)."""
        return await self._agent.arun(
            question, dog_id=self._dog_id, sleep_reader=self._sleep_reader
        )


def build_eval_agent(
    *,
    settings: AgentSettings | None = None,
    mode: RetrievalMode = "dense",
    web_search: WebSearch | None = None,
    pet_food: PetFoodLookup | None = None,
    memory_store: DogMemoryStore | None = None,
    dog_id: str | None = None,
    sleep_reader: SleepDataReader | None = None,
) -> EvalAgent:
    """Assemble the deterministic eval agent (real retriever, faked web + memory).

    mode selects the retriever configuration (dense or rerank) so the same
    harness scores either; hybrid stays unwired and the retriever rejects it.

    web_search / pet_food override the default empty fakes so an eval can feed the
    agent controlled tool output (for example the injection eval's poisoned web
    payloads). memory_store / dog_id / sleep_reader are the seams that make the
    memory and sleep tools reachable; all default to None, which keeps this a
    four-tool agent identical to what the committed generation baselines used.
    """
    resolved = build_eval_settings(settings)
    agent = PawPilotAgent(
        model=build_chat_model(resolved),
        retriever=build_retriever(mode=mode),
        web_search=web_search if web_search is not None else FakeWebSearch([]),
        pet_food=pet_food if pet_food is not None else FakePetFood([]),
        settings=resolved,
        checkpointer=None,
        memory_store=memory_store,
    )
    return EvalAgent(agent, mode=mode, dog_id=dog_id, sleep_reader=sleep_reader)


def build_full_eval_agent(
    *,
    settings: AgentSettings | None = None,
    mode: RetrievalMode = "dense",
    web_search: WebSearch | None = None,
    pet_food: PetFoodLookup | None = None,
    sleep_reader: SleepDataReader | None = None,
) -> EvalAgent:
    """An eval agent with all nine tools bound, for the tool-routing eval.

    Adds the three memory tools (via an in-memory ``DogMemoryStore`` plus the
    fixture ``EVAL_DOG_ID``) and the two sleep tools (via a fake reader) on top of
    the four always-on tools, so routing is measured over the full deployed
    surface. Kept separate from ``build_eval_agent`` so the generation eval is
    never silently switched onto a different, larger tool set.
    """
    return build_eval_agent(
        settings=settings,
        mode=mode,
        web_search=web_search,
        pet_food=pet_food,
        memory_store=DogMemoryStore(InMemoryStore()),
        dog_id=EVAL_DOG_ID,
        sleep_reader=sleep_reader if sleep_reader is not None else default_sleep_reader(),
    )
