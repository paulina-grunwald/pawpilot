"""Pydantic contracts for the Ask PawPilot agent.

`AgentAnswer` is the single value returned by `run_agent`: the grounded answer
text, the citations the model actually referenced, whether the red-flag pre-check
tripped, and which tools ran (for evaluation and observability).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.rag.schemas import SourceTier

CitationKind = Literal["corpus", "web"]


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
    """The grounded, cited answer to a single dog-health question."""

    model_config = ConfigDict(frozen=True)

    text: str
    citations: list[Citation]
    emergency: bool
    tool_calls: list[str]
