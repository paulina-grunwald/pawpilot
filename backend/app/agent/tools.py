"""The agent's two tools, bound to a single run's retriever, web search, and registry.

Each tool records its passages in the shared `CitationRegistry` (so the final
answer can resolve referenced ids) and appends its name to ``invoked_tools`` (so
the run reports which tools actually executed, even if the budget is exhausted).
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from app.agent.citations import CitationRegistry
from app.agent.web_search import WebSearch
from app.rag.retriever import VetCorpusRetriever

_NO_CORPUS_RESULTS = "No matching passages found in the veterinary corpus."
_NO_WEB_RESULTS = "No web results found."


def build_agent_tools(
    retriever: VetCorpusRetriever,
    web_search_backend: WebSearch,
    registry: CitationRegistry,
    invoked_tools: list[str],
    *,
    top_k: int,
) -> list[BaseTool]:
    """Build the corpus and web-search tools for one agent run."""

    @tool
    def retrieve_vet_corpus(query: str) -> str:
        """Search the veterinary literature corpus for passages relevant to a
        dog-health question. Returns numbered passages tagged [S1], [S2], … to
        cite. Prefer this for any health claim."""
        invoked_tools.append("retrieve_vet_corpus")
        chunks = retriever.retrieve(query, top_k=top_k)
        if not chunks:
            return _NO_CORPUS_RESULTS
        return registry.register_corpus_chunks(chunks)

    @tool
    def web_search(query: str) -> str:
        """Search the public web for current information such as product recalls,
        news, or topics the corpus does not cover. Returns numbered snippets
        tagged [W1], [W2], … to cite."""
        invoked_tools.append("web_search")
        results = web_search_backend.search(query)
        if not results:
            return _NO_WEB_RESULTS
        return registry.register_web_results(results)

    return [retrieve_vet_corpus, web_search]
