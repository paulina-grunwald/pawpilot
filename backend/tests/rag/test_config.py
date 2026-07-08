from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.config import RagSettings

_KEY_ALIASES = ("VERCEL_AI_GATEWAY", "AI_GATEWAY_API_KEY", "VERCEL_OIDC_TOKEN")


def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run in an empty cwd (no `.env`) with all RAG env vars cleared."""
    monkeypatch.chdir(tmp_path)
    for name in (*_KEY_ALIASES, "RAG_EMBED_MODEL", "RAG_GEN_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_reads_gateway_key_from_primary_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key-123")
    settings = RagSettings()
    assert settings.gateway_api_key == "key-123"
    assert settings.embed_model == "openai/text-embedding-3-small"
    assert settings.gen_model.startswith("openai/")
    assert settings.collection == "vet_corpus"
    assert settings.default_top_k == 8


def test_falls_back_to_ai_gateway_key_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "fallback-key")
    settings = RagSettings()
    assert settings.gateway_api_key == "fallback-key"


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    with pytest.raises(ValidationError):
        RagSettings()


def test_rejects_bare_embed_model_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_EMBED_MODEL", "text-embedding-3-small")  # no provider prefix
    with pytest.raises(ValidationError):
        RagSettings()


def test_rejects_bare_gen_model_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_GEN_MODEL", "gpt-5.4-mini")  # no provider prefix
    with pytest.raises(ValidationError):
        RagSettings()
