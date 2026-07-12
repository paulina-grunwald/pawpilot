"""Pydantic contracts for the Ask PawPilot agent.

`AgentAnswer` is the single value returned by `run_agent`: the grounded answer
text, the citations the model actually referenced, whether the red-flag pre-check
tripped, and which tools ran (for evaluation and observability).
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.rag.schemas import SourceTier

CitationKind = Literal["corpus", "web"]


class AgentAskRequest(BaseModel):
    """Request body for ``POST /agent/ask``.

    ``pet_id`` selects the dog whose long-term memory applies (owner-scoped);
    ``thread_id`` continues an existing conversation.
    """

    query: str = Field(max_length=4000)
    pet_id: uuid.UUID | None = None
    thread_id: str | None = Field(default=None, max_length=200)


class Citation(BaseModel):
    """A single source the answer referenced, keyed by its ``[S#]``/``[W#]`` id."""

    model_config = ConfigDict(frozen=True)

    ref: str
    kind: CitationKind
    title: str
    url: str
    source_id: str | None = None
    source_tier: SourceTier | None = None
    page_start: int | None = None


class AgentAnswer(BaseModel):
    """The grounded, cited answer to a single dog-health question.

    contexts carries the raw passages retrieval surfaced this run (corpus and
    web), for RAGAS generation metrics. It is exclude=True so it never reaches
    API clients: the vet corpus is private, and its text must not leak in the
    /agent/ask response body.
    """

    model_config = ConfigDict(frozen=True)

    text: str
    citations: list[Citation]
    emergency: bool
    tool_calls: list[str]
    contexts: list[str] = Field(default_factory=list, exclude=True)


class AgentStreamChunk(BaseModel):
    """One piece of streamed answer text."""

    type: Literal["token"] = "token"
    text: str


class AgentStreamFinal(BaseModel):
    """Closing event: the citations, emergency flag, and tools the run used."""

    type: Literal["final"] = "final"
    citations: list[Citation]
    emergency: bool
    tool_calls: list[str]


class AgentStreamError(BaseModel):
    """Terminal event when a streamed run fails."""

    type: Literal["error"] = "error"
    detail: str
