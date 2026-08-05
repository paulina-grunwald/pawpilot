"""The agent's retrieval tools, bound to a single run's backends and registry.

Each tool records its passages in the shared `CitationRegistry` (so the final
answer can resolve referenced ids) and appends its name to ``invoked_tools`` (so
the run reports which tools actually executed, even if the budget is exhausted).
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from app.agent.citations import CitationRegistry, ReferenceEntry
from app.agent.pet_food import PetFoodLookup
from app.agent.web_search import WebSearch
from app.rag.lookups import lookup_breed_norm, lookup_toxicity, size_category_for_weight
from app.rag.retriever import VetCorpusRetriever
from app.rag.schemas import BreedNorm, ToxicSubstance

_NO_CORPUS_RESULTS = "No matching passages found in the veterinary corpus."
_NO_WEB_RESULTS = "No web results found."
_NO_PET_FOOD_RESULTS = (
    "No matching pet-food product found in Open Pet Food Facts. That database is "
    "incomplete, so this does not mean the product does not exist. Call `web_search` "
    "for the product name before telling the owner you could not find it."
)
_NO_TOXICITY_MATCH = (
    "That substance is not in the curated toxicity table. This means it is unlisted, "
    "not that it is safe. Search the veterinary corpus before saying anything about it."
)
_NO_BREED_NORM_MATCH = (
    "No norms for that breed or size in the curated table. Search the veterinary corpus instead."
)


def _describe_toxicity(substance: ToxicSubstance) -> ReferenceEntry:
    """Render a toxic-substance row as a citable reference entry."""
    return ReferenceEntry(
        title=f"{substance.name} ({substance.category}, {substance.severity})",
        url=substance.source_url,
        body=(
            f"{substance.name} is toxic to dogs.\n"
            f"- Category: {substance.category}\n"
            f"- Severity: {substance.severity}\n"
            f"- Notes: {substance.notes}"
        ),
    )


def _describe_breed_norm(norm: BreedNorm) -> ReferenceEntry:
    """Render a breed-norm row as a citable reference entry."""
    heart_rate_low, heart_rate_high = norm.resting_heart_rate_range_bpm
    walk_low, walk_high = norm.daily_walk_target_km_range
    label = norm.breed if norm.breed is not None else f"{norm.size_category} dogs"
    return ReferenceEntry(
        title=f"Physiological norms for {label}",
        url=norm.source_url,
        body=(
            f"Norms for {label} (size category: {norm.size_category}).\n"
            f"- Resting heart rate: {heart_rate_low}-{heart_rate_high} bpm\n"
            f"- Sleeping respiratory rate: up to {norm.sleeping_respiratory_rate_max_bpm} "
            "breaths per minute\n"
            f"- Daily walk target: {walk_low}-{walk_high} km\n"
            f"- Considered senior from: {norm.senior_age_years} years"
        ),
    )


def build_agent_tools(
    retriever: VetCorpusRetriever,
    web_search_backend: WebSearch,
    pet_food_backend: PetFoodLookup,
    registry: CitationRegistry,
    invoked_tools: list[str],
    *,
    top_k: int,
) -> list[BaseTool]:
    """Build the corpus, web-search, pet-food, and exact-match lookup tools for one run."""

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

    @tool
    def lookup_pet_food(query: str) -> str:
        """Look up a commercial dog- or pet-food product by name (e.g. "Orijen Six
        Fish") or barcode in the Open Pet Food Facts database. Returns its
        guaranteed-analysis macros (crude protein, fat, fibre) and ingredient list,
        tagged [F1], [F2], … to cite. Use it for questions about a specific food's
        nutrition, macros, or ingredients."""
        invoked_tools.append("lookup_pet_food")
        products = pet_food_backend.lookup(query)
        if not products:
            return _NO_PET_FOOD_RESULTS
        return registry.register_food_products(products)

    @tool
    def lookup_toxic_substance(name: str) -> str:
        """Check whether a named substance is toxic to dogs, using a curated
        exact-match table (foods, plants, medications, household chemicals — e.g.
        "xylitol", "chocolate", "grapes", "ibuprofen"). Returns its category,
        severity, and clinical notes tagged [R1], [R2], … to cite. Prefer this over
        searching for any "is X poisonous/toxic to dogs" question. An unlisted
        substance is not a safe substance."""
        invoked_tools.append("lookup_toxic_substance")
        substance = lookup_toxicity(name)
        if substance is None:
            return _NO_TOXICITY_MATCH
        return registry.register_reference_entries([_describe_toxicity(substance)])

    @tool
    def lookup_breed_norms(breed: str = "", weight_grams: int = 0) -> str:
        """Look up healthy physiological ranges for a dog — resting heart rate,
        sleeping respiratory rate, daily walk target, and senior age. Pass the breed
        name when known; pass weight_grams as well (or instead, for a mixed or
        unknown breed) to fall back to the matching size category. Returns the norms
        tagged [R1], [R2], … to cite. Use it to judge whether one of this dog's
        measured vitals is actually abnormal."""
        invoked_tools.append("lookup_breed_norms")
        norm = lookup_breed_norm(
            breed=breed.strip() or None,
            size_category=size_category_for_weight(weight_grams) if weight_grams > 0 else None,
        )
        if norm is None:
            return _NO_BREED_NORM_MATCH
        return registry.register_reference_entries([_describe_breed_norm(norm)])

    return [
        retrieve_vet_corpus,
        web_search,
        lookup_pet_food,
        lookup_toxic_substance,
        lookup_breed_norms,
    ]
