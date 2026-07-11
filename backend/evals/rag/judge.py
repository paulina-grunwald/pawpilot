"""Gateway-backed RAGAS judge + generator

RAGAS is wired via its own llm_factory / embedding_factory fed a
synchronous openai.OpenAI client pointed at the Vercel AI Gateway. The
judge's async .agenerate is bridged onto the sync client via
asyncio.to_thread (RAGAS metric methods call agenerate; the Instructor
async path is unreliable in some runtimes).

Requires the evals dependency group:  uv sync --group evals
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


def _guard_empty_embedding_inputs(embeddings: Any) -> Any:
    """Coerce blank embedding inputs to a single space.

    The RAGAS prechunked transform pipeline can emit empty/whitespace-only
    nodes (e.g. zero-length headline splits). The Gateway rejects empty
    embedding inputs with a 400 (input cannot be an empty string), so we
    substitute a single space, which embeds cleanly and never matches real
    retrieval content.
    """
    embed_text = embeddings.embed_text
    embed_texts = embeddings.embed_texts

    def safe_embed_text(text: str, **kwargs: Any) -> Any:
        return embed_text(text if text.strip() else " ", **kwargs)

    def safe_embed_texts(texts: list[str], **kwargs: Any) -> Any:
        return embed_texts([text if text.strip() else " " for text in texts], **kwargs)

    embeddings.embed_text = safe_embed_text
    embeddings.embed_texts = safe_embed_texts
    return embeddings


def build_generator_embeddings(settings: RagSettings | None = None) -> Any:
    resolved = settings or get_rag_settings()
    embeddings = embedding_factory(
        "openai", model=resolved.embed_model, client=_gateway_client(resolved)
    )
    return _guard_empty_embedding_inputs(embeddings)


def build_sync_judge_llm(settings: RagSettings | None = None, model: str | None = None) -> Any:
    """RAGAS judge LLM whose async agenerate runs on the sync Gateway client.

    model overrides the judge model id (defaults to gen_model); the agent
    generation eval passes a distinct id to avoid grading answers with the model
    that produced them.
    """
    resolved = settings or get_rag_settings()
    judge = llm_factory(
        model or resolved.gen_model,
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
