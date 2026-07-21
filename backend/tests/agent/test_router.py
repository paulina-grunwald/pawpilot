"""HTTP-level tests for the ``/agent/ask`` and ``/agent/ask/stream`` endpoints.

These run against the real FastAPI app (with the test Postgres) but override the
``get_agent`` dependency with an in-memory fake, so they cover authentication,
owner-scoped pet resolution, per-user thread namespacing, thread recording, and
the validation / failure status codes without any model keys.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import date

from httpx import AsyncClient
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.fakes import ScriptedChatModel
from app.agent.models import AgentThread
from app.agent.prompt import DATA_TOOL_RULE, VET_DISCLAIMER
from app.agent.runner import PawPilotAgent
from app.config import settings
from app.integrations.tractive.models import TractiveDayRollup
from app.rate_limit import limiter
from tests.agent.conftest import RaisingChatModel, build_test_agent, make_chunk, tool_call_message


def _sleep_tool_call() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_dog_sleep_summary",
                "args": {"days": 7},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )


async def _create_pet(
    client: AsyncClient, valid_pet_payload: Callable[..., dict[str, object]]
) -> str:
    response = await client.post("/pets", json=valid_pet_payload())
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _current_user_id(client: AsyncClient) -> str:
    response = await client.get("/users/me")
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def _answer_agent() -> PawPilotAgent:
    return build_test_agent(
        responses=[AIMessage(content=f"Feed twice daily. {VET_DISCLAIMER}")],
        with_thread=True,
        with_memory=True,
    )


# --------------------------------------------------------------------------- #
# POST /agent/ask
# --------------------------------------------------------------------------- #


async def test_ask_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/agent/ask", json={"query": "hello"})
    assert response.status_code == 401


async def test_ask_rejects_empty_query(
    authenticated_client: AsyncClient, install_agent: Callable[[PawPilotAgent], None]
) -> None:
    install_agent(_answer_agent())
    response = await authenticated_client.post("/agent/ask", json={"query": "   "})
    assert response.status_code == 422


async def test_ask_rejects_oversize_query(
    authenticated_client: AsyncClient, install_agent: Callable[[PawPilotAgent], None]
) -> None:
    install_agent(_answer_agent())
    response = await authenticated_client.post("/agent/ask", json={"query": "x" * 2001})
    assert response.status_code == 422


async def test_ask_returns_answer_without_pet_or_thread(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
    db_session: AsyncSession,
) -> None:
    install_agent(_answer_agent())
    response = await authenticated_client.post("/agent/ask", json={"query": "How often to feed?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "Feed twice daily." in body["text"]
    assert body["emergency"] is False
    assert body["tool_calls"] == []
    # No thread id supplied -> nothing recorded.
    rows = (await db_session.execute(select(AgentThread))).scalars().all()
    assert rows == []


async def test_ask_rate_limited_after_the_configured_quota(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
) -> None:
    install_agent(_answer_agent())
    allowed = int(settings.agent_rate_limit.split("/")[0])
    # The limiter is disabled suite-wide (conftest); enable it just for this case,
    # reset its buckets so prior tests don't count, and restore on the way out.
    limiter.reset()
    limiter.enabled = True
    try:
        for _ in range(allowed):
            ok = await authenticated_client.post("/agent/ask", json={"query": "hi"})
            assert ok.status_code == 200, ok.text
        blocked = await authenticated_client.post("/agent/ask", json={"query": "hi"})
        assert blocked.status_code == 429
    finally:
        limiter.enabled = False
        limiter.reset()


async def test_ask_records_namespaced_thread(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
    db_session: AsyncSession,
) -> None:
    install_agent(_answer_agent())
    user_id = await _current_user_id(authenticated_client)

    response = await authenticated_client.post(
        "/agent/ask", json={"query": "Hi", "thread_id": "conv-1"}
    )
    assert response.status_code == 200, response.text

    rows = (await db_session.execute(select(AgentThread))).scalars().all()
    assert len(rows) == 1
    assert rows[0].thread_id == f"{user_id}:conv-1"
    assert str(rows[0].owner_user_id) == user_id


async def test_ask_resolves_owned_pet(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "diet"),
            AIMessage(content=f"Great question [S1]. {VET_DISCLAIMER}"),
        ],
        chunks=[make_chunk()],
        with_memory=True,
        with_thread=True,
    )
    install_agent(agent)
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)

    response = await authenticated_client.post(
        "/agent/ask", json={"query": "Diet tips?", "pet_id": pet_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tool_calls"] == ["retrieve_vet_corpus"]
    assert [citation["ref"] for citation in body["citations"]] == ["S1"]


async def test_ask_with_pet_reads_sleep_data_end_to_end(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    db_session.add(
        TractiveDayRollup(
            pet_id=uuid.UUID(pet_id),
            date=date(2024, 5, 16),
            minutes_night_sleep=480.0,
            minutes_day_sleep=0.0,
            source="gdpr_export",
        )
    )
    await db_session.commit()

    agent = build_test_agent(
        responses=[
            _sleep_tool_call(),
            AIMessage(content=f"Your dog slept about 8 hours a night. {VET_DISCLAIMER}"),
        ],
        with_memory=True,
        with_thread=True,
    )
    install_agent(agent)

    response = await authenticated_client.post(
        "/agent/ask", json={"query": "How much did my dog sleep?", "pet_id": pet_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tool_calls"] == ["get_dog_sleep_summary"]
    assert "8 hours" in body["text"]


async def test_ask_without_pet_omits_sleep_tool_rule(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
) -> None:
    model = ScriptedChatModel(responses=[AIMessage(content=f"Sure. {VET_DISCLAIMER}")])
    install_agent(build_test_agent(model=model))

    response = await authenticated_client.post("/agent/ask", json={"query": "General question"})
    assert response.status_code == 200, response.text

    system_messages = [
        str(message.content)
        for batch in model.received_batches
        for message in batch
        if message.type == "system"
    ]
    assert all(DATA_TOOL_RULE not in content for content in system_messages)


async def test_ask_rejects_unowned_pet(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
) -> None:
    install_agent(_answer_agent())
    response = await authenticated_client.post(
        "/agent/ask",
        json={"query": "Hi", "pet_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "PET_NOT_FOUND"


async def test_ask_returns_503_when_agent_fails(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
    db_session: AsyncSession,
) -> None:
    install_agent(build_test_agent(model=RaisingChatModel(), with_thread=True))
    response = await authenticated_client.post(
        "/agent/ask", json={"query": "Hi", "thread_id": "conv-x"}
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "AGENT_UNAVAILABLE"
    # A failed run must not record a thread.
    rows = (await db_session.execute(select(AgentThread))).scalars().all()
    assert rows == []


# --------------------------------------------------------------------------- #
# POST /agent/ask/stream
# --------------------------------------------------------------------------- #


def _parse_sse(raw: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:") :].strip()))
    return events


async def test_stream_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/agent/ask/stream", json={"query": "hello"})
    assert response.status_code == 401


async def test_stream_rejects_empty_query(
    authenticated_client: AsyncClient, install_agent: Callable[[PawPilotAgent], None]
) -> None:
    install_agent(_answer_agent())
    response = await authenticated_client.post("/agent/ask/stream", json={"query": ""})
    assert response.status_code == 422


async def test_stream_emits_token_and_final_events(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
    db_session: AsyncSession,
) -> None:
    install_agent(_answer_agent())
    async with authenticated_client.stream(
        "POST", "/agent/ask/stream", json={"query": "Hi", "thread_id": "conv-s"}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = await response.aread()

    events = _parse_sse(body.decode())
    types = [event["type"] for event in events]
    assert "token" in types
    assert types[-1] == "final"
    streamed = "".join(str(event["text"]) for event in events if event["type"] == "token")
    assert "Feed twice daily." in streamed

    rows = (await db_session.execute(select(AgentThread))).scalars().all()
    assert len(rows) == 1
    assert rows[0].thread_id.endswith(":conv-s")


async def test_stream_emits_error_event_when_agent_fails(
    authenticated_client: AsyncClient,
    install_agent: Callable[[PawPilotAgent], None],
) -> None:
    install_agent(build_test_agent(model=RaisingChatModel(), with_thread=True))
    async with authenticated_client.stream(
        "POST", "/agent/ask/stream", json={"query": "Hi"}
    ) as response:
        assert response.status_code == 200
        body = await response.aread()

    events = _parse_sse(body.decode())
    assert events[-1]["type"] == "error"
    assert events[-1]["detail"] == "AGENT_UNAVAILABLE"
