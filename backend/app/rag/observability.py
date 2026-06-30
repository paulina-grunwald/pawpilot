"""LangSmith observability wiring.

Tracing is opt-in via ``LANGSMITH_TRACING=true`` and **off in CI/tests**. The
non-obvious bit (carried from AIE10 Module 05): this account is on the EU
instance, so ``LANGSMITH_ENDPOINT`` must default to the EU URL *before* any
LangSmith client is constructed — the default US endpoint returns 403.
"""

from __future__ import annotations

import os

DEFAULT_LANGSMITH_ENDPOINT = "https://eu.api.smith.langchain.com"
DEFAULT_LANGSMITH_PROJECT = "pawpilot-rag"


def tracing_enabled() -> bool:
    """True only when ``LANGSMITH_TRACING`` is explicitly ``true``."""
    return os.environ.get("LANGSMITH_TRACING", "").strip().lower() == "true"


def configure_langsmith() -> bool:
    """Set EU endpoint + project defaults (idempotent); return whether tracing is on.

    Call once at app startup, before any LangSmith client is built.
    """
    os.environ.setdefault("LANGSMITH_ENDPOINT", DEFAULT_LANGSMITH_ENDPOINT)
    os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_LANGSMITH_PROJECT)
    return tracing_enabled()
