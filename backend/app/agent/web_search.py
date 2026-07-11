"""Web search behind a Protocol so tests never touch the network.

`TavilyWebSearch` is the production implementation (lazy-importing
`langchain-tavily` so unit tests need neither the package nor a key). Tests inject
`FakeWebSearch` from `app.agent.fakes`.
"""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

from app.agent.config import AgentSettings

_ALLOWED_URL_SCHEMES = ("http", "https")


def safe_http_url(raw_url: str) -> str:
    """Return the url only if it is http(s); otherwise blank it.

    Web results are attacker-controllable, so a ``javascript:`` or ``data:`` url
    must never survive into a citation the chat UI could render as a link.
    """
    scheme = urlsplit(raw_url.strip()).scheme.lower()
    return raw_url if scheme in _ALLOWED_URL_SCHEMES else ""


class WebSearchResult(BaseModel):
    """A single web result, normalized to the fields the agent cites."""

    title: str
    url: str
    content: str


class WebSearch(Protocol):
    """Structural interface for the agent's web-search backend."""

    def search(self, query: str) -> list[WebSearchResult]: ...


def parse_tavily_response(response: object) -> list[WebSearchResult]:
    """Normalize a Tavily ``invoke`` response into `WebSearchResult`s."""
    raw_results = response.get("results", []) if isinstance(response, dict) else []
    return [
        WebSearchResult(
            title=str(item.get("title", "")),
            url=safe_http_url(str(item.get("url", ""))),
            content=str(item.get("content", "")),
        )
        for item in raw_results
        if isinstance(item, dict)
    ]


class TavilyWebSearch:
    """Web search via Tavily through ``langchain-tavily``."""

    def __init__(self, settings: AgentSettings) -> None:
        from langchain_tavily import TavilySearch

        self._search = TavilySearch(
            max_results=settings.web_search_max_results,
            tavily_api_key=settings.tavily_api_key.get_secret_value(),
        )

    def search(self, query: str) -> list[WebSearchResult]:
        return parse_tavily_response(self._search.invoke({"query": query}))
