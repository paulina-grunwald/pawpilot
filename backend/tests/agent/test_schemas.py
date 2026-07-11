"""Tests for the Ask PawPilot agent Pydantic contracts in `app.agent.schemas`.

These assert the validation rules (length limits, uuid parsing, `Literal`
constraints), the frozen value objects, and the default `type` discriminators on
the streaming event models — no network, no DB, pure Pydantic behavior.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.agent.schemas import (
    AgentAnswer,
    AgentAskRequest,
    AgentStreamChunk,
    AgentStreamError,
    AgentStreamFinal,
    Citation,
)


def make_citation(**overrides: object) -> Citation:
    """A minimal valid `Citation` for the frozen-model and field tests."""
    values: dict[str, object] = {
        "ref": "S1",
        "kind": "corpus",
        "title": "WSAVA Vaccination Guidelines",
        "url": "https://example.org/wsava.pdf",
    }
    values.update(overrides)
    return Citation.model_validate(values)


# --------------------------------------------------------------------------- #
# AgentAskRequest — query
# --------------------------------------------------------------------------- #


def test_agent_ask_request_requires_query() -> None:
    with pytest.raises(ValidationError):
        AgentAskRequest.model_validate({})


def test_agent_ask_request_accepts_short_query() -> None:
    request = AgentAskRequest(query="Is kibble ok for my Aussie?")
    assert request.query == "Is kibble ok for my Aussie?"
    assert request.pet_id is None
    assert request.thread_id is None


def test_agent_ask_request_accepts_query_at_max_length() -> None:
    request = AgentAskRequest(query="x" * 4000)
    assert len(request.query) == 4000


def test_agent_ask_request_rejects_query_one_over_max_length() -> None:
    with pytest.raises(ValidationError):
        AgentAskRequest(query="x" * 4001)


def test_agent_ask_request_rejects_query_far_over_max_length() -> None:
    with pytest.raises(ValidationError):
        AgentAskRequest(query="x" * 5000)


def test_agent_ask_request_allows_empty_query_at_schema_level() -> None:
    # The schema has no min_length; the runner's validate_query is what rejects
    # blank queries (returning 422). This locks in that division of responsibility.
    request = AgentAskRequest(query="")
    assert request.query == ""


# --------------------------------------------------------------------------- #
# AgentAskRequest — thread_id
# --------------------------------------------------------------------------- #


def test_agent_ask_request_thread_id_defaults_to_none() -> None:
    request = AgentAskRequest(query="hello")
    assert request.thread_id is None


def test_agent_ask_request_accepts_thread_id() -> None:
    request = AgentAskRequest(query="hello", thread_id="thread-a")
    assert request.thread_id == "thread-a"


def test_agent_ask_request_accepts_thread_id_at_max_length() -> None:
    request = AgentAskRequest(query="hello", thread_id="t" * 200)
    assert request.thread_id is not None
    assert len(request.thread_id) == 200


def test_agent_ask_request_rejects_thread_id_over_max_length() -> None:
    with pytest.raises(ValidationError):
        AgentAskRequest(query="hello", thread_id="t" * 201)


# --------------------------------------------------------------------------- #
# AgentAskRequest — pet_id
# --------------------------------------------------------------------------- #


def test_agent_ask_request_pet_id_defaults_to_none() -> None:
    request = AgentAskRequest(query="hello")
    assert request.pet_id is None


def test_agent_ask_request_parses_pet_id_from_string() -> None:
    pet_uuid = uuid.uuid4()
    request = AgentAskRequest.model_validate({"query": "hello", "pet_id": str(pet_uuid)})
    assert request.pet_id == pet_uuid
    assert isinstance(request.pet_id, uuid.UUID)


def test_agent_ask_request_accepts_pet_id_uuid_instance() -> None:
    pet_uuid = uuid.uuid4()
    request = AgentAskRequest(query="hello", pet_id=pet_uuid)
    assert request.pet_id == pet_uuid


def test_agent_ask_request_rejects_invalid_pet_id() -> None:
    with pytest.raises(ValidationError):
        AgentAskRequest.model_validate({"query": "hello", "pet_id": "not-a-uuid"})


# --------------------------------------------------------------------------- #
# Citation — fields, defaults, and Literal constraint
# --------------------------------------------------------------------------- #


def test_citation_holds_all_fields() -> None:
    citation = Citation(
        ref="S1",
        kind="corpus",
        title="WSAVA Vaccination Guidelines",
        url="https://example.org/wsava.pdf",
        source_id="wsava-2024",
        source_tier="guideline",
        page_start=12,
    )
    assert citation.ref == "S1"
    assert citation.kind == "corpus"
    assert citation.title == "WSAVA Vaccination Guidelines"
    assert citation.url == "https://example.org/wsava.pdf"
    assert citation.source_id == "wsava-2024"
    assert citation.source_tier == "guideline"
    assert citation.page_start == 12


def test_citation_optional_fields_default_to_none() -> None:
    citation = make_citation()
    assert citation.source_id is None
    assert citation.source_tier is None
    assert citation.page_start is None


def test_citation_requires_ref_kind_title_url() -> None:
    with pytest.raises(ValidationError):
        Citation.model_validate({"ref": "S1", "kind": "corpus"})


def test_citation_accepts_corpus_kind() -> None:
    assert make_citation(kind="corpus").kind == "corpus"


def test_citation_accepts_web_kind() -> None:
    assert make_citation(kind="web").kind == "web"


def test_citation_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        make_citation(kind="podcast")


def test_citation_accepts_known_source_tier() -> None:
    assert make_citation(source_tier="primary_research").source_tier == "primary_research"


def test_citation_rejects_unknown_source_tier() -> None:
    with pytest.raises(ValidationError):
        make_citation(source_tier="rumor")


def test_citation_is_frozen() -> None:
    citation = make_citation()
    with pytest.raises(ValidationError):
        citation.ref = "S2"


# --------------------------------------------------------------------------- #
# AgentAnswer — fields and frozen
# --------------------------------------------------------------------------- #


def test_agent_answer_holds_fields() -> None:
    citation = make_citation()
    answer = AgentAnswer(
        text="Feed twice daily.",
        citations=[citation],
        emergency=False,
        tool_calls=["retrieve_vet_corpus"],
    )
    assert answer.text == "Feed twice daily."
    assert answer.citations == [citation]
    assert answer.emergency is False
    assert answer.tool_calls == ["retrieve_vet_corpus"]


def test_agent_answer_is_frozen() -> None:
    answer = AgentAnswer(text="hi", citations=[], emergency=False, tool_calls=[])
    with pytest.raises(ValidationError):
        answer.text = "changed"


def test_agent_answer_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        AgentAnswer.model_validate({"text": "hi"})


def test_agent_answer_contexts_default_to_empty_list() -> None:
    answer = AgentAnswer(text="hi", citations=[], emergency=False, tool_calls=[])
    assert answer.contexts == []


def test_agent_answer_holds_contexts() -> None:
    answer = AgentAnswer(
        text="hi",
        citations=[],
        emergency=False,
        tool_calls=[],
        contexts=["passage one", "passage two"],
    )
    assert answer.contexts == ["passage one", "passage two"]


def test_agent_answer_contexts_excluded_from_serialization() -> None:
    # The vet corpus is private; `contexts` must never appear in the API response
    # body, so it is excluded from both dict and JSON dumps.
    answer = AgentAnswer(
        text="hi",
        citations=[],
        emergency=False,
        tool_calls=[],
        contexts=["private corpus passage"],
    )
    assert "contexts" not in answer.model_dump()
    assert "private corpus passage" not in answer.model_dump_json()


# --------------------------------------------------------------------------- #
# AgentStreamChunk
# --------------------------------------------------------------------------- #


def test_agent_stream_chunk_type_defaults_to_token() -> None:
    chunk = AgentStreamChunk(text="partial answer")
    assert chunk.type == "token"
    assert chunk.text == "partial answer"


def test_agent_stream_chunk_requires_text() -> None:
    with pytest.raises(ValidationError):
        AgentStreamChunk.model_validate({})


def test_agent_stream_chunk_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        AgentStreamChunk.model_validate({"type": "final", "text": "oops"})


# --------------------------------------------------------------------------- #
# AgentStreamFinal
# --------------------------------------------------------------------------- #


def test_agent_stream_final_type_defaults_to_final() -> None:
    final = AgentStreamFinal(citations=[], emergency=False, tool_calls=[])
    assert final.type == "final"


def test_agent_stream_final_carries_payload() -> None:
    citation = make_citation()
    final = AgentStreamFinal(
        citations=[citation],
        emergency=True,
        tool_calls=["web_search"],
    )
    assert final.citations == [citation]
    assert final.emergency is True
    assert final.tool_calls == ["web_search"]


def test_agent_stream_final_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        AgentStreamFinal.model_validate({})


def test_agent_stream_final_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        AgentStreamFinal.model_validate(
            {"type": "token", "citations": [], "emergency": False, "tool_calls": []}
        )


# --------------------------------------------------------------------------- #
# AgentStreamError
# --------------------------------------------------------------------------- #


def test_agent_stream_error_type_defaults_to_error() -> None:
    error = AgentStreamError(detail="upstream timeout")
    assert error.type == "error"


def test_agent_stream_error_carries_detail() -> None:
    error = AgentStreamError(detail="upstream timeout")
    assert error.detail == "upstream timeout"


def test_agent_stream_error_requires_detail() -> None:
    with pytest.raises(ValidationError):
        AgentStreamError.model_validate({})


def test_agent_stream_error_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        AgentStreamError.model_validate({"type": "final", "detail": "boom"})
