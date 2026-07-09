"""RAG backbone (spec 009): vet-corpus retrieval + breed/toxicity lookups.

Phase 1 (spec 009a) ships dense retrieval over the veterinary corpus with full
citation metadata, plus the breed-norm and toxic-substance lookup tools. Hybrid
(009b) and reranking (009c) extend the retriever behind the same interfaces.
"""
