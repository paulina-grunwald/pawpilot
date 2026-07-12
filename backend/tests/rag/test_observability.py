from __future__ import annotations

import os
from pathlib import Path

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


def test_configure_enables_tracing_when_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-secret")
    assert configure_langsmith() is True
    assert tracing_enabled() is True


def test_configure_normalizes_alternate_truthy_tracing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("LANGSMITH_API_KEY", "LANGSMITH_ENDPOINT", "LANGSMITH_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "1")
    monkeypatch.chdir(tmp_path)
    assert configure_langsmith() is True
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert tracing_enabled() is True


def test_configure_promotes_key_from_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in (
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_PROJECT",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text("LANGSMITH_TRACING=true\nLANGSMITH_API_KEY=ls-from-dotenv\n")
    monkeypatch.chdir(tmp_path)
    assert configure_langsmith() is True
    assert os.environ["LANGSMITH_API_KEY"] == "ls-from-dotenv"


def test_configure_warns_when_tracing_on_but_key_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("LANGSMITH_API_KEY", "LANGSMITH_ENDPOINT", "LANGSMITH_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.chdir(tmp_path)
    assert configure_langsmith() is True
    assert "LANGSMITH_API_KEY" not in os.environ
    assert "traces will not export" in capsys.readouterr().out
