from __future__ import annotations

import os

import pytest

from app.rag.observability import (
    DEFAULT_LANGSMITH_ENDPOINT,
    DEFAULT_LANGSMITH_PROJECT,
    configure_langsmith,
    tracing_enabled,
)


def test_tracing_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert tracing_enabled() is False


def test_tracing_enabled_when_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "TRUE")
    assert tracing_enabled() is True


def test_configure_sets_eu_endpoint_and_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    enabled = configure_langsmith()
    assert os.environ["LANGSMITH_ENDPOINT"] == DEFAULT_LANGSMITH_ENDPOINT
    assert os.environ["LANGSMITH_PROJECT"] == DEFAULT_LANGSMITH_PROJECT
    assert enabled is False


def test_configure_respects_existing_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://custom.smith.example")
    configure_langsmith()
    assert os.environ["LANGSMITH_ENDPOINT"] == "https://custom.smith.example"


def test_configure_enables_and_promotes_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-secret")
    enabled = configure_langsmith()
    assert enabled is True
    assert tracing_enabled() is True
    assert os.environ["LANGSMITH_API_KEY"] == "ls-secret"
