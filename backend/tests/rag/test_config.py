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


def _clear_rerank_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("RAG_DEFAULT_MODE", "RAG_RERANK_MODEL", "RAG_RERANK_CANDIDATES"):
        monkeypatch.delenv(name, raising=False)


def test_rerank_settings_default_to_dense_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolated_env(monkeypatch, tmp_path)
    _clear_rerank_env(monkeypatch)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    settings = RagSettings()
    assert settings.default_mode == "dense"
    assert settings.rerank_model == "cohere/rerank-v3.5"
    assert settings.rerank_candidates == 25


def test_reads_rerank_settings_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    _clear_rerank_env(monkeypatch)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_DEFAULT_MODE", "rerank")
    monkeypatch.setenv("RAG_RERANK_MODEL", "cohere/rerank-v4-fast")
    monkeypatch.setenv("RAG_RERANK_CANDIDATES", "40")
    settings = RagSettings()
    assert settings.default_mode == "rerank"
    assert settings.rerank_model == "cohere/rerank-v4-fast"
    assert settings.rerank_candidates == 40


def test_rejects_bare_rerank_model_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    _clear_rerank_env(monkeypatch)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_RERANK_MODEL", "rerank-v3.5")
    with pytest.raises(ValidationError):
        RagSettings()


def test_rejects_invalid_default_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolated_env(monkeypatch, tmp_path)
    _clear_rerank_env(monkeypatch)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_DEFAULT_MODE", "sparse")  # not a RetrievalMode
    with pytest.raises(ValidationError):
        RagSettings()


@pytest.mark.parametrize("value", ["0", "201"])
def test_rejects_out_of_bounds_rerank_candidates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    _isolated_env(monkeypatch, tmp_path)
    _clear_rerank_env(monkeypatch)
    monkeypatch.delenv("RAG_DEFAULT_TOP_K", raising=False)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_RERANK_CANDIDATES", value)
    with pytest.raises(ValidationError):
        RagSettings()


def test_rejects_rerank_candidates_below_top_k(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The reranker cannot return more than it over-retrieves, so candidates < top_k
    # is a misconfiguration the settings must reject.
    _isolated_env(monkeypatch, tmp_path)
    _clear_rerank_env(monkeypatch)
    monkeypatch.delenv("RAG_DEFAULT_TOP_K", raising=False)
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "key")
    monkeypatch.setenv("RAG_RERANK_CANDIDATES", "5")  # below the default top_k of 8
    with pytest.raises(ValidationError, match="must be >= default_top_k"):
        RagSettings()
