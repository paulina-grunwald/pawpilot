"""Tests for the pure web-search helpers in `app.agent.web_search`.

These cover `safe_http_url` (the url allowlist that keeps ``javascript:`` and
other unsafe schemes out of citations), the `WebSearchResult` model, and
`parse_tavily_response` (which normalizes a raw Tavily payload). The networked
`TavilyWebSearch` is intentionally never constructed — it imports
``langchain-tavily`` and needs a key.
"""

from __future__ import annotations

import pytest

from app.agent.web_search import (
    TavilyWebSearch,
    WebSearchResult,
    parse_tavily_response,
    safe_http_url,
)

# --------------------------------------------------------------------------- #
# safe_http_url — allowed schemes
# --------------------------------------------------------------------------- #


def test_safe_http_url_passes_https_through_unchanged() -> None:
    url = "https://news.example.com/recall?lot=42#top"
    assert safe_http_url(url) == url


def test_safe_http_url_passes_http_through_unchanged() -> None:
    url = "http://example.org/page"
    assert safe_http_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "HTTPS://Example.com/Path",
        "Http://Example.com",
        "HtTpS://example.com",
    ],
)
def test_safe_http_url_scheme_check_is_case_insensitive(url: str) -> None:
    assert safe_http_url(url) == url


# --------------------------------------------------------------------------- #
# safe_http_url — rejected schemes and malformed input
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "ftp://files.example.com/pub",
        "mailto:vet@example.com",
        "file:///etc/passwd",
        "tel:+15550000000",
    ],
)
def test_safe_http_url_blanks_disallowed_schemes(url: str) -> None:
    assert safe_http_url(url) == ""


@pytest.mark.parametrize(
    "url",
    [
        "example.com/no-scheme",
        "/relative/path",
        "//protocol-relative.example.com",
        "just some text",
    ],
)
def test_safe_http_url_blanks_schemeless_urls(url: str) -> None:
    assert safe_http_url(url) == ""


def test_safe_http_url_blanks_empty_string() -> None:
    assert safe_http_url("") == ""


def test_safe_http_url_blanks_whitespace_only() -> None:
    assert safe_http_url("   \t\n ") == ""


def test_safe_http_url_strips_surrounding_whitespace_before_check() -> None:
    assert safe_http_url("  https://example.com/page  ") == "  https://example.com/page  "


def test_safe_http_url_returns_original_including_whitespace_when_allowed() -> None:
    padded = "\thttps://example.com\n"
    assert safe_http_url(padded) == padded


def test_safe_http_url_leading_whitespace_does_not_rescue_bad_scheme() -> None:
    assert safe_http_url("  javascript:alert(1)  ") == ""


# --------------------------------------------------------------------------- #
# WebSearchResult model
# --------------------------------------------------------------------------- #


def test_web_search_result_round_trips_all_fields() -> None:
    result = WebSearchResult(
        title="Brand X kibble recall",
        url="https://news.example.com/recall",
        content="The manufacturer recalled several lots this week.",
    )
    dumped = result.model_dump()
    assert dumped == {
        "title": "Brand X kibble recall",
        "url": "https://news.example.com/recall",
        "content": "The manufacturer recalled several lots this week.",
    }
    assert WebSearchResult.model_validate(dumped) == result


# --------------------------------------------------------------------------- #
# TavilyWebSearch.search delegation
# --------------------------------------------------------------------------- #


class _FakeTavilySearch:
    """Stands in for ``langchain_tavily.TavilySearch`` — records the invoke payload."""

    def __init__(self, response: object) -> None:
        self._response = response
        self.invoked_with: list[object] = []

    def invoke(self, payload: object) -> object:
        self.invoked_with.append(payload)
        return self._response


def test_tavily_web_search_forwards_query_and_parses_response() -> None:
    fake_search = _FakeTavilySearch(
        {"results": [{"title": "Recall", "url": "https://news.example.com", "content": "body"}]}
    )
    # Bypass __init__ (it imports langchain-tavily and needs a key) and inject the stub.
    web_search = object.__new__(TavilyWebSearch)
    object.__setattr__(web_search, "_search", fake_search)

    results = web_search.search("brand x recall")

    assert fake_search.invoked_with == [{"query": "brand x recall"}]
    assert results == [
        WebSearchResult(title="Recall", url="https://news.example.com", content="body")
    ]


def test_tavily_web_search_blanks_unsafe_urls_from_response() -> None:
    fake_search = _FakeTavilySearch(
        {"results": [{"title": "Sketchy", "url": "javascript:alert(1)", "content": "x"}]}
    )
    web_search = object.__new__(TavilyWebSearch)
    object.__setattr__(web_search, "_search", fake_search)

    results = web_search.search("q")

    assert results[0].url == ""


# --------------------------------------------------------------------------- #
# parse_tavily_response — happy path and coercion
# --------------------------------------------------------------------------- #


def test_parse_tavily_response_maps_results_to_models() -> None:
    response = {
        "results": [
            {
                "title": "Recall notice",
                "url": "https://news.example.com/recall",
                "content": "Several lots affected.",
            },
            {
                "title": "Vet advice",
                "url": "http://vet.example.org/advice",
                "content": "Consult your veterinarian.",
            },
        ]
    }
    parsed = parse_tavily_response(response)
    assert parsed == [
        WebSearchResult(
            title="Recall notice",
            url="https://news.example.com/recall",
            content="Several lots affected.",
        ),
        WebSearchResult(
            title="Vet advice",
            url="http://vet.example.org/advice",
            content="Consult your veterinarian.",
        ),
    ]


def test_parse_tavily_response_coerces_non_string_fields_to_str() -> None:
    response = {"results": [{"title": 42, "url": "https://example.com/x", "content": 3.5}]}
    parsed = parse_tavily_response(response)
    assert len(parsed) == 1
    assert parsed[0].title == "42"
    assert parsed[0].content == "3.5"
    assert parsed[0].url == "https://example.com/x"


def test_parse_tavily_response_blanks_unsafe_url() -> None:
    response = {
        "results": [
            {
                "title": "Sketchy",
                "url": "javascript:alert(1)",
                "content": "Do not click.",
            }
        ]
    }
    parsed = parse_tavily_response(response)
    assert parsed[0].url == ""
    assert parsed[0].title == "Sketchy"


def test_parse_tavily_response_defaults_missing_item_fields_to_empty() -> None:
    parsed = parse_tavily_response({"results": [{}]})
    assert parsed == [WebSearchResult(title="", url="", content="")]


def test_parse_tavily_response_defaults_partial_item_fields() -> None:
    parsed = parse_tavily_response({"results": [{"title": "Only a title"}]})
    assert parsed == [WebSearchResult(title="Only a title", url="", content="")]


# --------------------------------------------------------------------------- #
# parse_tavily_response — empty and malformed inputs
# --------------------------------------------------------------------------- #


def test_parse_tavily_response_empty_results_list() -> None:
    assert parse_tavily_response({"results": []}) == []


def test_parse_tavily_response_missing_results_key() -> None:
    assert parse_tavily_response({"other": "data"}) == []


def test_parse_tavily_response_empty_dict() -> None:
    assert parse_tavily_response({}) == []


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        "not a dict",
        42,
        ["results"],
    ],
)
def test_parse_tavily_response_non_dict_input_returns_empty(response: object) -> None:
    assert parse_tavily_response(response) == []


def test_parse_tavily_response_skips_non_dict_items() -> None:
    response = {
        "results": [
            "a bare string",
            {"title": "Kept", "url": "https://example.com", "content": "body"},
            None,
            42,
            ["nested", "list"],
        ]
    }
    parsed = parse_tavily_response(response)
    assert parsed == [WebSearchResult(title="Kept", url="https://example.com", content="body")]


def test_parse_tavily_response_all_items_skipped_returns_empty() -> None:
    assert parse_tavily_response({"results": ["x", None, 7]}) == []


def test_parse_tavily_response_results_not_a_list_of_dicts_is_iterated() -> None:
    # A string value under "results" is iterable; each character is not a dict,
    # so everything is skipped and the result is empty.
    assert parse_tavily_response({"results": "abc"}) == []
