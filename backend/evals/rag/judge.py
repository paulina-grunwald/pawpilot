"""Gateway-backed RAGAS judge + generator (lifted from AIE10 Module 06).

RAGAS is wired via its own ``llm_factory`` / ``embedding_factory`` fed a
synchronous ``openai.OpenAI`` client pointed at the Vercel AI Gateway. The
judge's async ``.agenerate`` is bridged onto the sync client via
``asyncio.to_thread`` (RAGAS metric methods call ``agenerate``; the Instructor
async path is unreliable in some runtimes).

Requires the ``evals`` dependency group:  uv sync --group evals
"""

from __future__ import annotations

import asyncio
from typing import Any

import instructor
from openai import OpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory

from app.rag.config import RagSettings, get_rag_settings


def _gateway_client(settings: RagSettings) -> OpenAI:
    return OpenAI(api_key=settings.gateway_api_key, base_url=settings.gateway_base_url)


def build_generator_llm(settings: RagSettings | None = None) -> Any:
    """Structured-output LLM for synthetic test-set generation."""
    resolved = settings or get_rag_settings()
    generator = llm_factory(
        resolved.gen_model,
        provider="openai",
        client=_gateway_client(resolved),
        mode=instructor.Mode.TOOLS,
        max_tokens=4096,
    )
    generator.model_args = {"max_tokens": 4096, "max_retries": 3}
    return generator


def build_generator_embeddings(settings: RagSettings | None = None) -> Any:
    resolved = settings or get_rag_settings()
    return embedding_factory("openai", model=resolved.embed_model, client=_gateway_client(resolved))


def build_sync_judge_llm(settings: RagSettings | None = None) -> Any:
    """RAGAS judge LLM whose async ``agenerate`` runs on the sync Gateway client."""
    resolved = settings or get_rag_settings()
    judge = llm_factory(
        resolved.gen_model,
        provider="openai",
        client=_gateway_client(resolved),
        mode=instructor.Mode.TOOLS,
        max_tokens=1024,
    )
    judge.model_args = {"max_tokens": 1024, "max_retries": 3}

    async def agenerate_from_sync(prompt: Any, response_model: Any) -> Any:
        return await asyncio.to_thread(judge.generate, prompt=prompt, response_model=response_model)

    judge.agenerate = agenerate_from_sync
    return judge
