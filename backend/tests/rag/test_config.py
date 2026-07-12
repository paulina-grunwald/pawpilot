from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.config import RagSettings

_KEY_ALIASES = ("VERCEL_AI_GATEWAY", "AI_GATEWAY_API_KEY", "VERCEL_OIDC_TOKEN")

# Every RagSettings validation alias. The default-value assertions below only hold
# in a clean environment, so all of these are cleared: an ambient shell or CI
# export of any RAG_* / QDRANT_* knob would otherwise perturb the built-in defaults.
_RAG_ENV_ALIASES = (
    *_KEY_ALIASES,
    "RAG_GATEWAY_BASE_URL",
    "RAG_EMBED_MODEL",
    "RAG_EMBED_DIMENSIONS",
    "RAG_EMBED_BATCH_SIZE",
    "RAG_GEN_MODEL",
    "AGENT_EVAL_JUDGE_MODEL",
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "RAG_COLLECTION",
    "RAG_DEFAULT_TOP_K",
    "RAG_FUSED_CANDIDATES",
)


def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run in an empty cwd (no `.env`) with every RAG env var cleared."""
    monkeypatch.chdir(tmp_path)
    for name in _RAG_ENV_ALIASES:
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
    assert settings.embed_batch_size == 128


def test_reads_embed_batch_size_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_EMBED_BATCH_SIZE", "64")
    assert RagSettings().embed_batch_size == 64


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
    monkeypatch.setenv("RAG_EMBED_MODEL", "text-embedding-3-small")
    with pytest.raises(ValidationError):
        RagSettings()


def test_rejects_bare_gen_model_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_GEN_MODEL", "gpt-5.4-mini")
    with pytest.raises(ValidationError):
        RagSettings()


def test_agent_eval_judge_model_defaults_to_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    assert RagSettings().agent_eval_judge_model is None


def test_reads_agent_eval_judge_model_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("AGENT_EVAL_JUDGE_MODEL", "openai/gpt-5.4")
    assert RagSettings().agent_eval_judge_model == "openai/gpt-5.4"


def test_rejects_bare_agent_eval_judge_model_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("AGENT_EVAL_JUDGE_MODEL", "gpt-5.4")
    with pytest.raises(ValidationError):
        RagSettings()
