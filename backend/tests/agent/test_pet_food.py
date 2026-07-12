"""Tests for the pure pet-food helpers and client in `app.agent.pet_food`.

These cover barcode detection, nutrient extraction from a raw ``nutriments`` block,
product-page url construction, the `PetFoodProduct` model (its title and passage
body), the response parsers, and `OpenPetFoodFactsClient.lookup` delegation against
a fake httpx client. The networked client is never constructed with a real socket —
its ``__init__`` is bypassed and a stub is injected, exactly as `TavilyWebSearch` is
tested.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.agent.pet_food import (
    _REQUESTED_FIELDS,
    OpenPetFoodFactsClient,
    PetFoodNutrient,
    PetFoodProduct,
    extract_nutrients,
    looks_like_barcode,
    parse_product,
    parse_product_response,
    parse_search_response,
    product_page_url,
)

_BASE_URL = "https://world.openpetfoodfacts.org"

# --------------------------------------------------------------------------- #
# looks_like_barcode
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "query",
    ["0064992281182", "064992281182", "  0064992281182  ", "123456"],
)
def test_looks_like_barcode_true_for_numeric_codes(query: str) -> None:
    assert looks_like_barcode(query) is True


@pytest.mark.parametrize(
    "query",
    ["orijen six fish", "12345", "", "   ", "acana", "64992-281182", "6 fish"],
)
def test_looks_like_barcode_false_for_names_and_short_input(query: str) -> None:
    assert looks_like_barcode(query) is False


# --------------------------------------------------------------------------- #
# product_page_url
# --------------------------------------------------------------------------- #


def test_product_page_url_builds_public_product_page() -> None:
    assert product_page_url(_BASE_URL, "0064992281182") == (
        "https://world.openpetfoodfacts.org/product/0064992281182"
    )


def test_product_page_url_strips_trailing_slash_from_base() -> None:
    assert product_page_url(_BASE_URL + "/", "123456") == (
        "https://world.openpetfoodfacts.org/product/123456"
    )


def test_product_page_url_blank_when_code_missing() -> None:
    assert product_page_url(_BASE_URL, "") == ""


# --------------------------------------------------------------------------- #
# extract_nutrients
# --------------------------------------------------------------------------- #


def test_extract_nutrients_pulls_guaranteed_analysis_in_order() -> None:
    nutriments = {
        "crude-protein": 40,
        "crude-fat": 19,
        "crude-fibre": 3,
        "crude-ash": 9,
        "moisture": 10,
    }
    nutrients = extract_nutrients(nutriments)
    assert [(nutrient.label, nutrient.value) for nutrient in nutrients] == [
        ("Crude protein", 40.0),
        ("Crude fat", 19.0),
        ("Crude fibre", 3.0),
        ("Crude ash", 9.0),
        ("Moisture", 10.0),
    ]
    assert all(nutrient.unit == "%" for nutrient in nutrients)


def test_extract_nutrients_coerces_numeric_strings() -> None:
    nutrients = extract_nutrients({"crude-protein": "38.5"})
    assert nutrients == [PetFoodNutrient(label="Crude protein", value=38.5)]


def test_extract_nutrients_skips_missing_and_non_numeric_keys() -> None:
    nutrients = extract_nutrients({"crude-protein": 40, "crude-fat": "n/a", "crude-fibre": None})
    assert [nutrient.label for nutrient in nutrients] == ["Crude protein"]


def test_extract_nutrients_ignores_booleans() -> None:
    assert extract_nutrients({"crude-protein": True}) == []


@pytest.mark.parametrize("nutriments", [None, [], "not a dict", 42])
def test_extract_nutrients_returns_empty_for_non_dict(nutriments: object) -> None:
    assert extract_nutrients(nutriments) == []


# --------------------------------------------------------------------------- #
# PetFoodProduct model
# --------------------------------------------------------------------------- #


def make_product(**overrides: Any) -> PetFoodProduct:
    values: dict[str, Any] = {
        "code": "0064992281182",
        "name": "Six Fish",
        "brands": "Orijen",
        "quantity": "1.8 kg",
        "ingredients_text": "Whole sardine, whole hake.",
        "nutrients": [
            PetFoodNutrient(label="Crude protein", value=40.0),
            PetFoodNutrient(label="Crude fibre", value=3.5),
        ],
        "url": f"{_BASE_URL}/product/0064992281182",
    }
    values.update(overrides)
    return PetFoodProduct.model_validate(values)


def test_display_title_combines_brand_and_name() -> None:
    assert make_product().display_title == "Orijen Six Fish"


def test_display_title_uses_name_only_when_brand_blank() -> None:
    assert make_product(brands="").display_title == "Six Fish"


def test_display_title_uses_brand_only_when_name_blank() -> None:
    assert make_product(name="").display_title == "Orijen"


def test_display_title_falls_back_to_code_when_unnamed() -> None:
    assert make_product(brands="", name="").display_title == "0064992281182"


def test_display_title_falls_back_to_placeholder_without_code() -> None:
    assert make_product(brands="", name="", code="").display_title == "Unknown product"


def test_describe_lists_pack_size_analysis_and_ingredients() -> None:
    described = make_product().describe()
    assert "Pack size: 1.8 kg" in described
    assert "Guaranteed analysis:" in described
    assert "- Crude protein: 40%" in described
    assert "- Crude fibre: 3.5%" in described
    assert "Ingredients: Whole sardine, whole hake." in described


def test_describe_formats_whole_numbers_without_trailing_zero() -> None:
    product = make_product(nutrients=[PetFoodNutrient(label="Crude protein", value=40.0)])
    described = product.describe()
    assert "40%" in described
    assert "40.0%" not in described


def test_describe_reports_when_no_nutrition_available() -> None:
    described = make_product(nutrients=[]).describe()
    assert "No nutrition data available." in described


# --------------------------------------------------------------------------- #
# parse_product
# --------------------------------------------------------------------------- #


def test_parse_product_normalizes_full_record() -> None:
    raw = {
        "code": "0064992281182",
        "product_name": "Six Fish",
        "brands": "Orijen",
        "quantity": "1.8 kg",
        "ingredients_text": "Whole sardine.",
        "nutriments": {"crude-protein": 40, "crude-fat": 19},
    }
    product = parse_product(raw, base_url=_BASE_URL)
    assert product is not None
    assert product.code == "0064992281182"
    assert product.name == "Six Fish"
    assert product.brands == "Orijen"
    assert product.url == f"{_BASE_URL}/product/0064992281182"
    assert [nutrient.label for nutrient in product.nutrients] == ["Crude protein", "Crude fat"]


def test_parse_product_keeps_record_with_name_but_no_nutrition() -> None:
    product = parse_product({"code": "1", "product_name": "Mystery Kibble"}, base_url=_BASE_URL)
    assert product is not None
    assert product.name == "Mystery Kibble"
    assert product.nutrients == []


def test_parse_product_keeps_record_with_nutrition_but_no_name() -> None:
    product = parse_product({"code": "1", "nutriments": {"crude-protein": 30}}, base_url=_BASE_URL)
    assert product is not None
    assert product.name == ""
    assert [nutrient.label for nutrient in product.nutrients] == ["Crude protein"]


def test_parse_product_drops_record_with_neither_name_nor_nutrition() -> None:
    assert parse_product({"code": "1", "brands": "Orijen"}, base_url=_BASE_URL) is None


@pytest.mark.parametrize("raw", [None, [], "not a dict", 42])
def test_parse_product_returns_none_for_non_dict(raw: object) -> None:
    assert parse_product(raw, base_url=_BASE_URL) is None


# --------------------------------------------------------------------------- #
# parse_search_response
# --------------------------------------------------------------------------- #


def test_parse_search_response_maps_products_up_to_limit() -> None:
    response = {
        "products": [
            {"code": "1", "product_name": "First", "nutriments": {"crude-protein": 40}},
            {"code": "2", "product_name": "Second", "nutriments": {"crude-protein": 30}},
            {"code": "3", "product_name": "Third"},
        ]
    }
    products = parse_search_response(response, base_url=_BASE_URL, limit=2)
    assert [product.name for product in products] == ["First", "Second"]


def test_parse_search_response_skips_unusable_products() -> None:
    response = {
        "products": [
            {"code": "1", "brands": "NoName"},
            {"code": "2", "product_name": "Kept"},
            "a bare string",
        ]
    }
    products = parse_search_response(response, base_url=_BASE_URL, limit=5)
    assert [product.name for product in products] == ["Kept"]


@pytest.mark.parametrize("response", [None, {}, {"products": "not a list"}, 42, []])
def test_parse_search_response_empty_for_bad_payloads(response: object) -> None:
    assert parse_search_response(response, base_url=_BASE_URL, limit=5) == []


# --------------------------------------------------------------------------- #
# parse_product_response
# --------------------------------------------------------------------------- #


def test_parse_product_response_returns_product_when_found() -> None:
    response = {
        "status": 1,
        "product": {"code": "1", "product_name": "Six Fish", "nutriments": {"crude-protein": 40}},
    }
    products = parse_product_response(response, base_url=_BASE_URL)
    assert [product.name for product in products] == ["Six Fish"]


def test_parse_product_response_empty_when_status_not_found() -> None:
    response = {"status": 0, "status_verbose": "product not found"}
    assert parse_product_response(response, base_url=_BASE_URL) == []


def test_parse_product_response_empty_when_product_unusable() -> None:
    response = {"status": 1, "product": {"code": "1", "brands": "NoName"}}
    assert parse_product_response(response, base_url=_BASE_URL) == []


@pytest.mark.parametrize("response", [None, {}, "not a dict", {"status": 1}])
def test_parse_product_response_empty_for_bad_payloads(response: object) -> None:
    assert parse_product_response(response, base_url=_BASE_URL) == []


# --------------------------------------------------------------------------- #
# OpenPetFoodFactsClient.lookup delegation
# --------------------------------------------------------------------------- #


class _FakeHttpResponse:
    """Stands in for an httpx.Response — replays a payload or raises on demand."""

    def __init__(self, payload: object, *, status_error: Exception | None = None) -> None:
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeHttpClient:
    """Records the path and params of each ``get`` and returns a canned response."""

    def __init__(self, response: _FakeHttpResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def get(self, path: str, params: dict[str, object] | None = None) -> _FakeHttpResponse:
        self.calls.append((path, params))
        return self._response


def make_client(fake_http: _FakeHttpClient, *, max_results: int = 3) -> OpenPetFoodFactsClient:
    """Build a client with its ``__init__`` bypassed and a stub http client injected."""
    client = object.__new__(OpenPetFoodFactsClient)
    object.__setattr__(client, "_base_url", _BASE_URL)
    object.__setattr__(client, "_max_results", max_results)
    object.__setattr__(client, "_client", fake_http)
    return client


def test_lookup_empty_query_makes_no_request() -> None:
    fake_http = _FakeHttpClient(_FakeHttpResponse({"products": []}))
    client = make_client(fake_http)
    assert client.lookup("   ") == []
    assert fake_http.calls == []


def test_lookup_barcode_hits_product_endpoint() -> None:
    payload = {
        "status": 1,
        "product": {"code": "0064992281182", "product_name": "Six Fish"},
    }
    fake_http = _FakeHttpClient(_FakeHttpResponse(payload))
    client = make_client(fake_http)

    products = client.lookup("0064992281182")

    assert [product.name for product in products] == ["Six Fish"]
    path, params = fake_http.calls[0]
    assert path == "/api/v2/product/0064992281182.json"
    assert params == {"fields": _REQUESTED_FIELDS}


def test_lookup_name_hits_search_endpoint_with_expected_params() -> None:
    payload = {"products": [{"code": "1", "product_name": "Six Fish"}]}
    fake_http = _FakeHttpClient(_FakeHttpResponse(payload))
    client = make_client(fake_http, max_results=3)

    products = client.lookup("orijen six fish")

    assert [product.name for product in products] == ["Six Fish"]
    path, params = fake_http.calls[0]
    assert path == "/cgi/search.pl"
    assert params == {
        "search_terms": "orijen six fish",
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 3,
        "fields": _REQUESTED_FIELDS,
    }


def test_lookup_returns_empty_on_http_error() -> None:
    fake_http = _FakeHttpClient(_FakeHttpResponse({}, status_error=httpx.HTTPError("boom")))
    client = make_client(fake_http)
    assert client.lookup("orijen") == []


def test_lookup_returns_empty_on_non_json_body() -> None:
    fake_http = _FakeHttpClient(_FakeHttpResponse(ValueError("not json")))
    client = make_client(fake_http)
    assert client.lookup("orijen") == []
