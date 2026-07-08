"""Dev/QA retrieval endpoint: ``POST /rag/search`` (auth-gated, read-only).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

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
        try:
            _retriever = build_retriever()
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG_UNAVAILABLE",
            ) from error
    return _retriever


# TODO(009b): remove this dev/QA endpoint once the RAG agent consumes the
# retriever directly. get_retriever()/build_retriever() stay; only this route goes.
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
    except ValidationError as error:  # a stored Qdrant payload is corrupt
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG_PAYLOAD_CORRUPT",
        ) from error
    except Exception as error:  # Qdrant / Gateway unreachable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG_UNAVAILABLE",
        ) from error
    return RagSearchResponse(results=results)
