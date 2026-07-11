"""Tests for `AgentSettings` and the `get_agent_settings` accessor.

These exercise the model validator (required gateway key, provider-qualified
model), the field bounds, alias resolution from environment variables, and the
``lru_cache`` wrapping of ``get_agent_settings`` — all without a real ``.env``
(every direct construction passes ``_env_file=None``) and without a network.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from app.agent.config import AgentSettings, get_agent_settings
from tests.agent.conftest import make_agent_settings

# --------------------------------------------------------------------------- #
# model_validator — required gateway key
# --------------------------------------------------------------------------- #


def test_empty_gateway_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Vercel AI Gateway key is required"):
        make_agent_settings(gateway_api_key=SecretStr(""))


def test_valid_gateway_key_is_accepted() -> None:
    settings = make_agent_settings(gateway_api_key=SecretStr("real-key"))
    assert settings.gateway_api_key.get_secret_value() == "real-key"


# --------------------------------------------------------------------------- #
# model_validator — provider-qualified agent_model
# --------------------------------------------------------------------------- #


def test_agent_model_without_slash_is_rejected() -> None:
    with pytest.raises(ValidationError, match="provider-qualified"):
        make_agent_settings(agent_model="gpt5")


def test_agent_model_error_message_echoes_the_bad_value() -> None:
    with pytest.raises(ValidationError, match="'bare-model'"):
        make_agent_settings(agent_model="bare-model")


def test_provider_qualified_agent_model_is_accepted() -> None:
    settings = make_agent_settings(agent_model="anthropic/claude-opus")
    assert settings.agent_model == "anthropic/claude-opus"


# --------------------------------------------------------------------------- #
# Defaults on a valid construction
# --------------------------------------------------------------------------- #


def test_valid_construction_exposes_expected_defaults() -> None:
    settings = make_agent_settings()
    assert settings.agent_model == "openai/gpt-5.4-mini"
    assert settings.agent_temperature == pytest.approx(0.1)
    assert settings.agent_max_tool_calls == 6
    assert settings.memory_backend == "memory"
    assert settings.max_dog_memories == 20
    assert settings.memory_pool_max_size == 20
    assert settings.web_search_max_results == 5


def test_default_gateway_base_url() -> None:
    settings = make_agent_settings()
    assert settings.gateway_base_url == "https://ai-gateway.vercel.sh/v1"


def test_tavily_key_defaults_to_empty_and_is_not_required() -> None:
    settings = make_agent_settings()
    assert settings.tavily_api_key.get_secret_value() == ""


# --------------------------------------------------------------------------- #
# Bounds — agent_temperature ∈ [0.0, 2.0]
# --------------------------------------------------------------------------- #


def test_agent_temperature_above_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(agent_temperature=3.0)


def test_agent_temperature_below_min_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(agent_temperature=-0.1)


@pytest.mark.parametrize("temperature", [0.0, 2.0])
def test_agent_temperature_accepts_inclusive_bounds(temperature: float) -> None:
    settings = make_agent_settings(agent_temperature=temperature)
    assert settings.agent_temperature == pytest.approx(temperature)


# --------------------------------------------------------------------------- #
# Bounds — agent_max_tool_calls ∈ [1, 20]
# --------------------------------------------------------------------------- #


def test_agent_max_tool_calls_below_min_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(agent_max_tool_calls=0)


def test_agent_max_tool_calls_above_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(agent_max_tool_calls=21)


@pytest.mark.parametrize("max_tool_calls", [1, 20])
def test_agent_max_tool_calls_accepts_inclusive_bounds(max_tool_calls: int) -> None:
    settings = make_agent_settings(agent_max_tool_calls=max_tool_calls)
    assert settings.agent_max_tool_calls == max_tool_calls


# --------------------------------------------------------------------------- #
# Bounds — max_dog_memories ∈ [1, 100]
# --------------------------------------------------------------------------- #


def test_max_dog_memories_below_min_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(max_dog_memories=0)


def test_max_dog_memories_above_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(max_dog_memories=101)


@pytest.mark.parametrize("max_memories", [1, 100])
def test_max_dog_memories_accepts_inclusive_bounds(max_memories: int) -> None:
    settings = make_agent_settings(max_dog_memories=max_memories)
    assert settings.max_dog_memories == max_memories


# --------------------------------------------------------------------------- #
# Bounds — memory_pool_max_size ∈ [1, 100]
# --------------------------------------------------------------------------- #


def test_memory_pool_max_size_below_min_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(memory_pool_max_size=0)


def test_memory_pool_max_size_above_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(memory_pool_max_size=101)


@pytest.mark.parametrize("pool_size", [1, 100])
def test_memory_pool_max_size_accepts_inclusive_bounds(pool_size: int) -> None:
    settings = make_agent_settings(memory_pool_max_size=pool_size)
    assert settings.memory_pool_max_size == pool_size


# --------------------------------------------------------------------------- #
# Bounds — web_search_max_results ∈ [1, 20]
# --------------------------------------------------------------------------- #


def test_web_search_max_results_below_min_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(web_search_max_results=0)


def test_web_search_max_results_above_max_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(web_search_max_results=21)


@pytest.mark.parametrize("max_results", [1, 20])
def test_web_search_max_results_accepts_inclusive_bounds(max_results: int) -> None:
    settings = make_agent_settings(web_search_max_results=max_results)
    assert settings.web_search_max_results == max_results


# --------------------------------------------------------------------------- #
# memory_backend literal
# --------------------------------------------------------------------------- #


def test_memory_backend_accepts_postgres() -> None:
    settings = make_agent_settings(memory_backend="postgres")
    assert settings.memory_backend == "postgres"


def test_memory_backend_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        make_agent_settings(memory_backend="sqlite")


# --------------------------------------------------------------------------- #
# Environment alias resolution
# --------------------------------------------------------------------------- #


def test_gateway_key_read_from_vercel_ai_gateway_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.gateway_api_key.get_secret_value() == "env-gateway-key"


def test_gateway_key_read_from_ai_gateway_api_key_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VERCEL_AI_GATEWAY", raising=False)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "alt-gateway-key")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.gateway_api_key.get_secret_value() == "alt-gateway-key"


def test_gateway_key_read_from_vercel_oidc_token_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VERCEL_AI_GATEWAY", raising=False)
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", "oidc-gateway-key")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.gateway_api_key.get_secret_value() == "oidc-gateway-key"


def test_agent_model_read_from_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.setenv("AGENT_MODEL", "anthropic/claude-sonnet")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.agent_model == "anthropic/claude-sonnet"


def test_agent_temperature_read_from_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.setenv("AGENT_TEMPERATURE", "0.7")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.agent_temperature == pytest.approx(0.7)


def test_memory_backend_read_from_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.setenv("MEMORY_BACKEND", "postgres")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.memory_backend == "postgres"


def test_tavily_key_read_from_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.setenv("TAVILY", "tavily-key")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.tavily_api_key.get_secret_value() == "tavily-key"


def test_tavily_key_read_from_primary_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.delenv("TAVILY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "primary-tavily-key")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.tavily_api_key.get_secret_value() == "primary-tavily-key"


def test_gateway_base_url_read_from_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.setenv("RAG_GATEWAY_BASE_URL", "https://gateway.internal/v2")
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.gateway_base_url == "https://gateway.internal/v2"


@pytest.mark.parametrize(
    ("env_var", "raw_value", "attribute", "expected"),
    [
        ("AGENT_MAX_TOOL_CALLS", "9", "agent_max_tool_calls", 9),
        ("WEB_SEARCH_MAX_RESULTS", "7", "web_search_max_results", 7),
        ("MAX_DOG_MEMORIES", "42", "max_dog_memories", 42),
        ("AGENT_MEMORY_POOL_MAX_SIZE", "15", "memory_pool_max_size", 15),
    ],
)
def test_numeric_fields_read_from_env_aliases(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
    raw_value: str,
    attribute: str,
    expected: int,
) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "env-gateway-key")
    monkeypatch.setenv(env_var, raw_value)
    settings = AgentSettings(_env_file=None)  # type: ignore[call-arg]
    assert getattr(settings, attribute) == expected


# --------------------------------------------------------------------------- #
# get_agent_settings — lru_cache behavior
# --------------------------------------------------------------------------- #


def test_get_agent_settings_returns_cached_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "cache-test-key")
    get_agent_settings.cache_clear()
    try:
        first = get_agent_settings()
        second = get_agent_settings()
        assert isinstance(first, AgentSettings)
        assert first is second
    finally:
        get_agent_settings.cache_clear()


def test_get_agent_settings_rebuilds_after_cache_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL_AI_GATEWAY", "cache-test-key")
    get_agent_settings.cache_clear()
    try:
        first = get_agent_settings()
        get_agent_settings.cache_clear()
        second = get_agent_settings()
        assert first is not second
    finally:
        get_agent_settings.cache_clear()
