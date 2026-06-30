"""Dev/QA retrieval endpoint: ``POST /rag/search`` (auth-gated, read-only).

Spec 010's agent calls `VetCorpusRetriever` directly in-process; this HTTP
surface exists for manual QA and stays in production builds (read-only + behind
auth). The retriever is a DI seam (`get_retriever`) so tests inject a fake.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.auth.deps import current_active_user
from app.auth.models import User
from app.rag.retriever import VetCorpusRetriever, build_retriever
from app.rag.schemas import RagSearchRequest, RagSearchResponse, RetrievedChunk

rag_router = APIRouter(prefix="/rag", tags=["rag"])

_retriever: VetCorpusRetriever | None = None


def get_retriever() -> VetCorpusRetriever:
    """Lazily build a process-wide retriever (overridden in tests)."""
    global _retriever
    if _retriever is None:
        _retriever = build_retriever()
    return _retriever


@rag_router.post("/search", response_model=RagSearchResponse)
async def search_corpus(
    payload: RagSearchRequest,
    user: User = Depends(current_active_user),
    retriever: VetCorpusRetriever = Depends(get_retriever),
) -> RagSearchResponse:
    try:
        # retrieve() is sync (embed + Qdrant); run it off the event loop.
        results: list[RetrievedChunk] = await run_in_threadpool(
            retriever.retrieve,
            payload.query,
            top_k=payload.top_k,
            sources=payload.sources,
            source_tiers=payload.source_tiers,
        )
    except Exception as error:  # Qdrant / Gateway unreachable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG_UNAVAILABLE",
        ) from error
    return RagSearchResponse(results=results)
