"""Tests for the agent's two tools built by `build_agent_tools`.

Each tool is exercised through its public ``invoke`` surface: the corpus tool
registers ``[S#]`` passages in the shared `CitationRegistry` and records its name
in ``invoked_tools``; the web tool does the same with ``[W#]`` snippets. Empty
backends return the fixed no-result sentinels, and ``top_k`` is threaded through
to the retriever. Everything here is pure logic — no DB, no network, no keys.
"""

from __future__ import annotations

from typing import cast

from langchain_core.tools import BaseTool

from app.agent.citations import CitationRegistry
from app.agent.fakes import FakeWebSearch
from app.agent.tools import _NO_CORPUS_RESULTS, _NO_WEB_RESULTS, build_agent_tools
from app.agent.web_search import WebSearchResult
from app.rag.retriever import VetCorpusRetriever
from app.rag.schemas import RetrievalMode, RetrievedChunk, SourceTier
from tests.agent.conftest import StubRetriever, make_chunk, make_web_result

# --------------------------------------------------------------------------- #
# Local helpers
# --------------------------------------------------------------------------- #


class RecordingRetriever:
    """A retriever that records the ``top_k`` each call received.

    Duck-typed like `StubRetriever` (composition + a ``cast`` at the call site),
    but it captures the ``top_k`` argument so a test can assert it was threaded
    through from ``build_agent_tools``.
    """

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = list(chunks)
        self.recorded_top_k: list[int | None] = []

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        sources: list[str] | None = None,
        source_tiers: list[SourceTier] | None = None,
        mode: RetrievalMode = "dense",
    ) -> list[RetrievedChunk]:
        self.recorded_top_k.append(top_k)
        if top_k is None:
            return list(self._chunks)
        return list(self._chunks[:top_k])


def build_tools(
    *,
    chunks: list[RetrievedChunk] | None = None,
    web_results: list[WebSearchResult] | None = None,
    top_k: int = 5,
) -> tuple[list[BaseTool], CitationRegistry, list[str]]:
    """Wire a fresh registry, `StubRetriever`, and `FakeWebSearch` into the tools."""
    registry = CitationRegistry()
    retriever = cast(VetCorpusRetriever, StubRetriever(chunks if chunks is not None else []))
    web_search_backend = FakeWebSearch(web_results if web_results is not None else [])
    invoked_tools: list[str] = []
    tools = build_agent_tools(
        retriever,
        web_search_backend,
        registry,
        invoked_tools,
        top_k=top_k,
    )
    return tools, registry, invoked_tools


def get_corpus_tool(tools: list[BaseTool]) -> BaseTool:
    """The ``retrieve_vet_corpus`` tool from a built pair."""
    return next(tool for tool in tools if tool.name == "retrieve_vet_corpus")


def get_web_tool(tools: list[BaseTool]) -> BaseTool:
    """The ``web_search`` tool from a built pair."""
    return next(tool for tool in tools if tool.name == "web_search")


def invoke_tool(tool: BaseTool, query: str) -> str:
    """Invoke a tool with a single ``query`` argument and assert it returns text."""
    result = tool.invoke({"query": query})
    assert isinstance(result, str)
    return result


# --------------------------------------------------------------------------- #
# build_agent_tools — shape
# --------------------------------------------------------------------------- #


def test_build_agent_tools_returns_two_tools() -> None:
    tools, _registry, _invoked_tools = build_tools()
    assert len(tools) == 2
    assert all(isinstance(tool, BaseTool) for tool in tools)


def test_build_agent_tools_returns_expected_tool_names() -> None:
    tools, _registry, _invoked_tools = build_tools()
    assert [tool.name for tool in tools] == ["retrieve_vet_corpus", "web_search"]


def test_build_agent_tools_tools_have_descriptions() -> None:
    tools, _registry, _invoked_tools = build_tools()
    assert all(tool.description for tool in tools)


# --------------------------------------------------------------------------- #
# retrieve_vet_corpus — with results
# --------------------------------------------------------------------------- #


def test_retrieve_vet_corpus_returns_numbered_passage() -> None:
    tools, _registry, _invoked_tools = build_tools(chunks=[make_chunk()])
    result = invoke_tool(get_corpus_tool(tools), "vaccine booster")
    assert "[S1]" in result
    assert "WSAVA Vaccination Guidelines" in result
    assert "Adult dogs need a core booster every three years." in result


def test_retrieve_vet_corpus_appends_invoked_tool_name() -> None:
    tools, _registry, invoked_tools = build_tools(chunks=[make_chunk()])
    invoke_tool(get_corpus_tool(tools), "vaccine booster")
    assert invoked_tools == ["retrieve_vet_corpus"]


def test_retrieve_vet_corpus_registers_corpus_citation() -> None:
    tools, registry, _invoked_tools = build_tools(chunks=[make_chunk()])
    invoke_tool(get_corpus_tool(tools), "vaccine booster")
    citations = registry.resolve(["S1"])
    assert len(citations) == 1
    citation = citations[0]
    assert citation.ref == "S1"
    assert citation.kind == "corpus"
    assert citation.title == "WSAVA Vaccination Guidelines"
    assert citation.url == "https://example.org/wsava.pdf"
    assert citation.source_id == "wsava-2024"
    assert citation.source_tier == "guideline"
    assert citation.page_start == 12


def test_retrieve_vet_corpus_numbers_multiple_chunks() -> None:
    tools, registry, _invoked_tools = build_tools(
        chunks=[make_chunk(), make_chunk(chunk_id="chunk-2", title="Second Source")]
    )
    result = invoke_tool(get_corpus_tool(tools), "diet")
    assert "[S1]" in result
    assert "[S2]" in result
    assert [citation.ref for citation in registry.resolve(["S1", "S2"])] == ["S1", "S2"]


def test_retrieve_vet_corpus_continues_ids_across_calls() -> None:
    tools, registry, invoked_tools = build_tools(chunks=[make_chunk()])
    corpus_tool = get_corpus_tool(tools)
    first = invoke_tool(corpus_tool, "first")
    second = invoke_tool(corpus_tool, "second")
    assert "[S1]" in first
    assert "[S2]" in second
    assert invoked_tools == ["retrieve_vet_corpus", "retrieve_vet_corpus"]
    assert [citation.ref for citation in registry.resolve(["S1", "S2"])] == ["S1", "S2"]


# --------------------------------------------------------------------------- #
# retrieve_vet_corpus — empty
# --------------------------------------------------------------------------- #


def test_retrieve_vet_corpus_returns_sentinel_when_empty() -> None:
    tools, _registry, _invoked_tools = build_tools(chunks=[])
    result = invoke_tool(get_corpus_tool(tools), "nothing here")
    assert result == _NO_CORPUS_RESULTS


def test_retrieve_vet_corpus_still_records_name_when_empty() -> None:
    tools, _registry, invoked_tools = build_tools(chunks=[])
    invoke_tool(get_corpus_tool(tools), "nothing here")
    assert invoked_tools == ["retrieve_vet_corpus"]


def test_retrieve_vet_corpus_registers_nothing_when_empty() -> None:
    tools, registry, _invoked_tools = build_tools(chunks=[])
    invoke_tool(get_corpus_tool(tools), "nothing here")
    assert registry.resolve(["S1"]) == []


# --------------------------------------------------------------------------- #
# top_k pass-through
# --------------------------------------------------------------------------- #


def test_retrieve_vet_corpus_truncates_stub_results_to_top_k() -> None:
    tools, registry, _invoked_tools = build_tools(
        chunks=[
            make_chunk(chunk_id="chunk-1"),
            make_chunk(chunk_id="chunk-2"),
            make_chunk(chunk_id="chunk-3"),
        ],
        top_k=1,
    )
    result = invoke_tool(get_corpus_tool(tools), "vaccine")
    assert "[S1]" in result
    assert "[S2]" not in result
    assert len(registry.resolve(["S1", "S2", "S3"])) == 1


def test_retrieve_vet_corpus_passes_top_k_to_retriever() -> None:
    registry = CitationRegistry()
    recording_retriever = RecordingRetriever([make_chunk(), make_chunk(chunk_id="chunk-2")])
    web_search_backend = FakeWebSearch([])
    invoked_tools: list[str] = []
    tools = build_agent_tools(
        cast(VetCorpusRetriever, recording_retriever),
        web_search_backend,
        registry,
        invoked_tools,
        top_k=3,
    )
    invoke_tool(get_corpus_tool(tools), "vaccine")
    assert recording_retriever.recorded_top_k == [3]


# --------------------------------------------------------------------------- #
# web_search — with results
# --------------------------------------------------------------------------- #


def test_web_search_returns_numbered_snippet() -> None:
    tools, _registry, _invoked_tools = build_tools(web_results=[make_web_result()])
    result = invoke_tool(get_web_tool(tools), "brand x recall")
    assert "[W1]" in result
    assert "Brand X kibble recall" in result
    assert "https://news.example.com/recall" in result


def test_web_search_appends_invoked_tool_name() -> None:
    tools, _registry, invoked_tools = build_tools(web_results=[make_web_result()])
    invoke_tool(get_web_tool(tools), "brand x recall")
    assert invoked_tools == ["web_search"]


def test_web_search_registers_web_citation() -> None:
    tools, registry, _invoked_tools = build_tools(web_results=[make_web_result()])
    invoke_tool(get_web_tool(tools), "brand x recall")
    citations = registry.resolve(["W1"])
    assert len(citations) == 1
    citation = citations[0]
    assert citation.ref == "W1"
    assert citation.kind == "web"
    assert citation.title == "Brand X kibble recall"
    assert citation.url == "https://news.example.com/recall"


def test_web_search_numbers_multiple_results() -> None:
    tools, registry, _invoked_tools = build_tools(
        web_results=[
            make_web_result(),
            make_web_result(title="Second story", url="https://news.example.com/second"),
        ]
    )
    result = invoke_tool(get_web_tool(tools), "recalls")
    assert "[W1]" in result
    assert "[W2]" in result
    assert [citation.ref for citation in registry.resolve(["W1", "W2"])] == ["W1", "W2"]


# --------------------------------------------------------------------------- #
# web_search — empty
# --------------------------------------------------------------------------- #


def test_web_search_returns_sentinel_when_empty() -> None:
    tools, _registry, _invoked_tools = build_tools(web_results=[])
    result = invoke_tool(get_web_tool(tools), "nothing")
    assert result == _NO_WEB_RESULTS


def test_web_search_still_records_name_when_empty() -> None:
    tools, _registry, invoked_tools = build_tools(web_results=[])
    invoke_tool(get_web_tool(tools), "nothing")
    assert invoked_tools == ["web_search"]


def test_web_search_registers_nothing_when_empty() -> None:
    tools, registry, _invoked_tools = build_tools(web_results=[])
    invoke_tool(get_web_tool(tools), "nothing")
    assert registry.resolve(["W1"]) == []


# --------------------------------------------------------------------------- #
# Both tools sharing one run's registry and invoked_tools list
# --------------------------------------------------------------------------- #


def test_both_tools_share_invoked_tools_in_call_order() -> None:
    tools, _registry, invoked_tools = build_tools(
        chunks=[make_chunk()], web_results=[make_web_result()]
    )
    invoke_tool(get_corpus_tool(tools), "vaccine")
    invoke_tool(get_web_tool(tools), "recall")
    assert invoked_tools == ["retrieve_vet_corpus", "web_search"]


def test_both_tools_register_independent_id_series() -> None:
    tools, registry, _invoked_tools = build_tools(
        chunks=[make_chunk()], web_results=[make_web_result()]
    )
    corpus_result = invoke_tool(get_corpus_tool(tools), "vaccine")
    web_result = invoke_tool(get_web_tool(tools), "recall")
    assert "[S1]" in corpus_result
    assert "[W1]" in web_result
    resolved = registry.resolve(["S1", "W1"])
    assert [citation.kind for citation in resolved] == ["corpus", "web"]
