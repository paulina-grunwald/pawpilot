"""Pet-food nutrition lookups via the Open Pet Food Facts API, behind a Protocol.

OpenPetFoodFactsClient is the production implementation (an httpx call to the
public Open Pet Food Facts database); tests inject FakePetFood from
app.agent.fakes so they never touch the network. A query is either a barcode
(all digits, resolved against the product endpoint) or a free-text product name
(resolved against the search endpoint). Both paths normalize into PetFoodProduct,
surfacing the guaranteed-analysis macros and ingredient list the agent reasons over.
"""

from __future__ import annotations

from typing import Protocol
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.agent.config import AgentSettings

_SEARCH_PATH = "/cgi/search.pl"
_PRODUCT_PATH_TEMPLATE = "/api/v2/product/{barcode}.json"
_REQUESTED_FIELDS = "code,product_name,brands,quantity,ingredients_text,nutriments"
_MIN_BARCODE_DIGITS = 6

# Open Pet Food Facts stores the same guaranteed-analysis macro under two key
# styles: pet-food "crude-*" keys and generic Open Food Facts keys (proteins/
# fat/fiber). We read the crude key first and fall back to the generic one, so a
# product entered either way still surfaces its macros rather than looking empty.
_GUARANTEED_ANALYSIS_NUTRIENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Crude protein", ("crude-protein", "proteins")),
    ("Crude fat", ("crude-fat", "fat")),
    ("Crude fibre", ("crude-fibre", "fiber", "fibre")),
    ("Crude ash", ("crude-ash", "ash")),
    ("Moisture", ("moisture",)),
)


def looks_like_barcode(query: str) -> bool:
    """True when the query is a bare numeric barcode rather than a product name."""
    stripped = query.strip()
    return stripped.isdigit() and len(stripped) >= _MIN_BARCODE_DIGITS


def _coerce_number(raw: object) -> float | None:
    """Coerce a nutriment value to a float, or None if it is not numeric."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw.strip())
        except ValueError:
            return None
    return None


def _first_number(nutriments: dict[object, object], keys: tuple[str, ...]) -> float | None:
    """The first candidate key present as a numeric value; earlier keys win."""
    for key in keys:
        value = _coerce_number(nutriments.get(key))
        if value is not None:
            return value
    return None


def _format_number(value: float) -> str:
    """Render a nutrient value without a trailing ``.0`` (40.0 -> "40", 3.5 -> "3.5")."""
    return str(int(value)) if value == int(value) else str(value)


def product_page_url(base_url: str, code: str) -> str:
    """The public Open Pet Food Facts product page for a barcode, or blank if none."""
    if not code:
        return ""
    return f"{base_url.rstrip('/')}/product/{quote(code, safe='')}"


class PetFoodNutrient(BaseModel):
    """One nutrient from a product's guaranteed analysis (value as a percentage)."""

    label: str
    value: float
    unit: str = "%"


class PetFoodProduct(BaseModel):
    """A pet-food product normalized to the fields the agent cites and reasons over."""

    code: str
    name: str
    brands: str
    quantity: str
    ingredients_text: str
    nutrients: list[PetFoodNutrient]
    url: str

    @property
    def display_title(self) -> str:
        """A human title combining brand and product name, e.g. "Orijen Six Fish"."""
        parts = [part for part in (self.brands, self.name) if part]
        return " ".join(parts) if parts else (self.code or "Unknown product")

    def describe(self) -> str:
        """The passage body the model reads: guaranteed analysis then ingredients."""
        lines: list[str] = []
        if self.quantity:
            lines.append(f"Pack size: {self.quantity}")
        if self.nutrients:
            lines.append("Guaranteed analysis:")
            lines.extend(
                f"- {nutrient.label}: {_format_number(nutrient.value)}{nutrient.unit}"
                for nutrient in self.nutrients
            )
        else:
            lines.append("No nutrition data available.")
        if self.ingredients_text:
            lines.append(f"Ingredients: {self.ingredients_text}")
        return "\n".join(lines)


def extract_nutrients(nutriments: object) -> list[PetFoodNutrient]:
    """Pull the guaranteed-analysis macros from a raw ``nutriments`` block."""
    if not isinstance(nutriments, dict):
        return []
    nutrients: list[PetFoodNutrient] = []
    for label, keys in _GUARANTEED_ANALYSIS_NUTRIENTS:
        value = _first_number(nutriments, keys)
        if value is not None:
            nutrients.append(PetFoodNutrient(label=label, value=value))
    return nutrients


def parse_product(raw: object, *, base_url: str) -> PetFoodProduct | None:
    """Normalize one raw product; return None when it carries nothing the model can use."""
    if not isinstance(raw, dict):
        return None
    code = str(raw.get("code", "")).strip()
    name = str(raw.get("product_name", "")).strip()
    nutrients = extract_nutrients(raw.get("nutriments"))
    # A product with neither a name nor any nutrition is noise, not an answer.
    if not name and not nutrients:
        return None
    return PetFoodProduct(
        code=code,
        name=name,
        brands=str(raw.get("brands", "")).strip(),
        quantity=str(raw.get("quantity", "")).strip(),
        ingredients_text=str(raw.get("ingredients_text", "")).strip(),
        nutrients=nutrients,
        url=product_page_url(base_url, code),
    )


def parse_search_response(response: object, *, base_url: str, limit: int) -> list[PetFoodProduct]:
    """Normalize a ``search.pl`` payload into up to ``limit`` usable products."""
    raw_products = response.get("products") if isinstance(response, dict) else None
    if not isinstance(raw_products, list):
        return []
    products: list[PetFoodProduct] = []
    for raw in raw_products:
        product = parse_product(raw, base_url=base_url)
        if product is not None:
            products.append(product)
        if len(products) >= limit:
            break
    return products


def parse_product_response(response: object, *, base_url: str) -> list[PetFoodProduct]:
    """Normalize a single-product (barcode) payload; empty unless a product was found."""
    if not isinstance(response, dict) or response.get("status") != 1:
        return []
    product = parse_product(response.get("product"), base_url=base_url)
    return [product] if product is not None else []


class PetFoodLookup(Protocol):
    """Structural interface for the agent's pet-food lookup backend."""

    def lookup(self, query: str) -> list[PetFoodProduct]: ...


class OpenPetFoodFactsClient:
    """Pet-food lookups against the public Open Pet Food Facts API via httpx."""

    def __init__(self, settings: AgentSettings) -> None:
        self._base_url = settings.pet_food_base_url.rstrip("/")
        self._max_results = settings.pet_food_max_results
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=settings.pet_food_timeout_seconds,
            headers={"User-Agent": settings.pet_food_user_agent},
        )

    def lookup(self, query: str) -> list[PetFoodProduct]:
        """Look up a product by barcode or name; blank on empty input or any failure."""
        stripped = query.strip()
        if not stripped:
            return []
        try:
            if looks_like_barcode(stripped):
                return self._lookup_barcode(stripped)
            return self._search(stripped)
        except (httpx.HTTPError, ValueError):
            # Network trouble or a non-JSON body must not crash a run: the agent
            # treats an empty result as "no product found" and moves on.
            return []

    def _lookup_barcode(self, barcode: str) -> list[PetFoodProduct]:
        response = self._client.get(
            _PRODUCT_PATH_TEMPLATE.format(barcode=barcode),
            params={"fields": _REQUESTED_FIELDS},
        )
        response.raise_for_status()
        return parse_product_response(response.json(), base_url=self._base_url)

    def _search(self, query: str) -> list[PetFoodProduct]:
        response = self._client.get(
            _SEARCH_PATH,
            params={
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": self._max_results,
                "fields": _REQUESTED_FIELDS,
            },
        )
        response.raise_for_status()
        return parse_search_response(
            response.json(), base_url=self._base_url, limit=self._max_results
        )
