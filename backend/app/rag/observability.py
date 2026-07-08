"""LangSmith observability wiring."""

from __future__ import annotations

import os

DEFAULT_LANGSMITH_ENDPOINT = "https://eu.api.smith.langchain.com"
DEFAULT_LANGSMITH_PROJECT = "pawpilot-rag"


def tracing_enabled() -> bool:
    """True only when ``LANGSMITH_TRACING`` is explicitly ``true``."""
    return os.environ.get("LANGSMITH_TRACING", "").strip().lower() == "true"


def configure_langsmith() -> bool:
    """Set EU endpoint
    Call once at app startup, before any LangSmith client is built.
    """
    os.environ.setdefault("LANGSMITH_ENDPOINT", DEFAULT_LANGSMITH_ENDPOINT)
    os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_LANGSMITH_PROJECT)
    return tracing_enabled()
