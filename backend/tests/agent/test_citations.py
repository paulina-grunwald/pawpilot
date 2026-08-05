"""Tests for citation capture: `extract_referenced_ids` and `CitationRegistry`.

These exercise the pure-logic citation layer without keys, a network, or a graph:
id extraction from answer text, sequential ``[S#]``/``[W#]`` assignment that
continues across calls, the passage/snippet formatting handed to the model, and
resolution of referenced ids back to `Citation` objects.
"""

from __future__ import annotations

from app.agent.citations import CitationRegistry, ReferenceEntry, extract_referenced_ids
from app.agent.schemas import Citation
from tests.agent.conftest import make_chunk, make_pet_food_product, make_web_result

# --------------------------------------------------------------------------- #
# extract_referenced_ids
# --------------------------------------------------------------------------- #


def test_extract_returns_empty_for_text_without_ids() -> None:
    assert extract_referenced_ids("A plain answer with no citations.") == []


def test_extract_returns_empty_for_empty_string() -> None:
    assert extract_referenced_ids("") == []


def test_extract_finds_single_corpus_id() -> None:
    assert extract_referenced_ids("Boost every three years [S1].") == ["S1"]


def test_extract_finds_single_web_id() -> None:
    assert extract_referenced_ids("There was a recall [W1].") == ["W1"]


def test_extract_finds_single_food_id() -> None:
    assert extract_referenced_ids("That food is 40% protein [F1].") == ["F1"]


def test_extract_preserves_first_seen_order() -> None:
    text = "See [S2] and [S1], then also [W1] and [F1]."
    assert extract_referenced_ids(text) == ["S2", "S1", "W1", "F1"]


def test_extract_dedupes_repeated_ids_keeping_first_position() -> None:
    text = "Per [S2] and [S1]; again [S2]; and [S1] once more."
    assert extract_referenced_ids(text) == ["S2", "S1"]


def test_extract_handles_multi_digit_ids() -> None:
    assert extract_referenced_ids("Deep cite [S12] and [W34].") == ["S12", "W34"]


def test_extract_finds_adjacent_ids() -> None:
    assert extract_referenced_ids("[S1][W1]") == ["S1", "W1"]


def test_extract_finds_ids_nested_in_double_brackets() -> None:
    assert extract_referenced_ids("[[S1]]") == ["S1"]


def test_extract_ignores_unknown_letter_prefix() -> None:
    assert extract_referenced_ids("Not a ref [X1] here.") == []


def test_extract_ignores_lowercase_letter() -> None:
    assert extract_referenced_ids("lowercase [s1] is not a ref") == []


def test_extract_ignores_bracket_without_digits() -> None:
    assert extract_referenced_ids("bare [S] and [W] tags") == []


def test_extract_ignores_bare_number_bracket() -> None:
    assert extract_referenced_ids("footnote [1] style") == []


def test_extract_ignores_two_letter_prefix() -> None:
    assert extract_referenced_ids("combined [SW1] token") == []


def test_extract_ignores_trailing_non_digit_inside_bracket() -> None:
    assert extract_referenced_ids("malformed [S1a] token") == []


def test_extract_mixes_valid_and_invalid_brackets() -> None:
    text = "Valid [S1], junk [X9], valid [W2], junk [S], done."
    assert extract_referenced_ids(text) == ["S1", "W2"]


# --------------------------------------------------------------------------- #
# CitationRegistry.register_corpus_chunks
# --------------------------------------------------------------------------- #


def test_register_corpus_chunks_returns_empty_string_for_no_chunks() -> None:
    registry = CitationRegistry()
    assert registry.register_corpus_chunks([]) == ""


def test_register_corpus_chunks_formats_single_passage() -> None:
    registry = CitationRegistry()
    chunk = make_chunk()
    passages = registry.register_corpus_chunks([chunk])
    assert passages == (
        "[S1] WSAVA Vaccination Guidelines (p.12)\n"
        "Adult dogs need a core booster every three years."
    )


def test_register_corpus_chunks_passage_contains_ref_title_page_and_text() -> None:
    registry = CitationRegistry()
    chunk = make_chunk(title="Nutrition Basics", page_start=7, text="Feed to condition.")
    passages = registry.register_corpus_chunks([chunk])
    assert "[S1]" in passages
    assert "Nutrition Basics" in passages
    assert "(p.7)" in passages
    assert "Feed to condition." in passages


def test_register_corpus_chunks_numbers_sequentially_within_one_call() -> None:
    registry = CitationRegistry()
    passages = registry.register_corpus_chunks(
        [make_chunk(), make_chunk(chunk_id="chunk-2", title="Second Source")]
    )
    assert "[S1] WSAVA Vaccination Guidelines" in passages
    assert "[S2] Second Source" in passages
    assert passages.count("\n\n") == 1


def test_register_corpus_chunks_continues_ids_across_calls() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    second = registry.register_corpus_chunks([make_chunk(chunk_id="chunk-2", title="Later Source")])
    assert second.startswith("[S2] Later Source")


def test_register_corpus_chunks_builds_citation_with_chunk_metadata() -> None:
    registry = CitationRegistry()
    chunk = make_chunk(
        source_id="wsava-2024",
        source_tier="guideline",
        page_start=12,
        url="https://example.org/wsava.pdf",
        title="WSAVA Vaccination Guidelines",
    )
    registry.register_corpus_chunks([chunk])
    citation = registry.resolve(["S1"])[0]
    assert citation == Citation(
        ref="S1",
        kind="corpus",
        title="WSAVA Vaccination Guidelines",
        url="https://example.org/wsava.pdf",
        source_id="wsava-2024",
        source_tier="guideline",
        page_start=12,
    )


def test_register_corpus_chunks_citation_kind_is_corpus() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    assert registry.resolve(["S1"])[0].kind == "corpus"


# --------------------------------------------------------------------------- #
# CitationRegistry.register_web_results
# --------------------------------------------------------------------------- #


def test_register_web_results_returns_empty_string_for_no_results() -> None:
    registry = CitationRegistry()
    assert registry.register_web_results([]) == ""


def test_register_web_results_formats_single_snippet() -> None:
    registry = CitationRegistry()
    result = make_web_result()
    snippets = registry.register_web_results([result])
    assert snippets == (
        "[W1] Brand X kibble recall (https://news.example.com/recall)\n"
        "The manufacturer recalled several lots this week."
    )


def test_register_web_results_snippet_contains_ref_title_url_and_content() -> None:
    registry = CitationRegistry()
    result = make_web_result(
        title="Heat advisory", url="https://weather.example.com/heat", content="Keep dogs cool."
    )
    snippets = registry.register_web_results([result])
    assert "[W1]" in snippets
    assert "Heat advisory" in snippets
    assert "(https://weather.example.com/heat)" in snippets
    assert "Keep dogs cool." in snippets


def test_register_web_results_numbers_sequentially_within_one_call() -> None:
    registry = CitationRegistry()
    snippets = registry.register_web_results(
        [make_web_result(), make_web_result(title="Second recall")]
    )
    assert "[W1] Brand X kibble recall" in snippets
    assert "[W2] Second recall" in snippets
    assert snippets.count("\n\n") == 1


def test_register_web_results_continues_ids_across_calls() -> None:
    registry = CitationRegistry()
    registry.register_web_results([make_web_result()])
    second = registry.register_web_results([make_web_result(title="Later recall")])
    assert second.startswith("[W2] Later recall")


def test_register_web_results_builds_citation_with_title_and_url_only() -> None:
    registry = CitationRegistry()
    result = make_web_result(title="Brand X recall", url="https://news.example.com/recall")
    registry.register_web_results([result])
    citation = registry.resolve(["W1"])[0]
    assert citation == Citation(
        ref="W1",
        kind="web",
        title="Brand X recall",
        url="https://news.example.com/recall",
    )
    assert citation.source_id is None
    assert citation.source_tier is None
    assert citation.page_start is None


# --------------------------------------------------------------------------- #
# CitationRegistry.register_food_products
# --------------------------------------------------------------------------- #


def test_register_food_products_returns_empty_string_for_no_products() -> None:
    registry = CitationRegistry()
    assert registry.register_food_products([]) == ""


def test_register_food_products_formats_single_passage() -> None:
    registry = CitationRegistry()
    passages = registry.register_food_products([make_pet_food_product()])
    assert passages.startswith(
        "[F1] Orijen Six Fish (https://world.openpetfoodfacts.org/product/0064992281182)\n"
    )
    assert "- Crude protein: 40%" in passages
    assert "Ingredients: Whole sardine, whole hake, whole mackerel." in passages


def test_register_food_products_numbers_sequentially_within_one_call() -> None:
    registry = CitationRegistry()
    passages = registry.register_food_products(
        [make_pet_food_product(), make_pet_food_product(code="2", name="Regional Red")]
    )
    assert "[F1] Orijen Six Fish" in passages
    assert "[F2] Orijen Regional Red" in passages
    assert passages.count("\n\n") == 1


def test_register_food_products_continues_ids_across_calls() -> None:
    registry = CitationRegistry()
    registry.register_food_products([make_pet_food_product()])
    second = registry.register_food_products([make_pet_food_product(name="Later Food")])
    assert second.startswith("[F2] Orijen Later Food")


def test_register_food_products_builds_citation_with_title_and_url_only() -> None:
    registry = CitationRegistry()
    registry.register_food_products([make_pet_food_product()])
    citation = registry.resolve(["F1"])[0]
    assert citation == Citation(
        ref="F1",
        kind="food",
        title="Orijen Six Fish",
        url="https://world.openpetfoodfacts.org/product/0064992281182",
    )
    assert citation.source_id is None
    assert citation.page_start is None


# --------------------------------------------------------------------------- #
# CitationRegistry.resolve
# --------------------------------------------------------------------------- #


def test_resolve_returns_empty_for_no_referenced_ids() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    assert registry.resolve([]) == []


def test_resolve_returns_empty_when_registry_is_empty() -> None:
    registry = CitationRegistry()
    assert registry.resolve(["S1", "W1"]) == []


def test_resolve_preserves_referenced_order() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk(), make_chunk(chunk_id="chunk-2")])
    resolved = registry.resolve(["S2", "S1"])
    assert [citation.ref for citation in resolved] == ["S2", "S1"]


def test_resolve_silently_drops_unknown_ids() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    resolved = registry.resolve(["S1", "S99", "W1"])
    assert [citation.ref for citation in resolved] == ["S1"]


def test_resolve_keeps_duplicate_referenced_ids() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    resolved = registry.resolve(["S1", "S1"])
    assert [citation.ref for citation in resolved] == ["S1", "S1"]


# --------------------------------------------------------------------------- #
# Mixed corpus + web run
# --------------------------------------------------------------------------- #


def test_corpus_and_web_counters_are_independent() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    registry.register_web_results([make_web_result()])
    registry.register_corpus_chunks([make_chunk(chunk_id="chunk-2")])
    registry.register_web_results([make_web_result(title="Second recall")])

    resolved = registry.resolve(["S1", "S2", "W1", "W2"])
    assert [citation.ref for citation in resolved] == ["S1", "S2", "W1", "W2"]
    assert [citation.kind for citation in resolved] == ["corpus", "corpus", "web", "web"]


def test_mixed_run_resolves_ids_in_answer_order() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk(title="Corpus Source")])
    registry.register_web_results([make_web_result(title="Web Source")])

    referenced = extract_referenced_ids("Per [W1] and [S1], here is the plan.")
    resolved = registry.resolve(referenced)
    assert [citation.ref for citation in resolved] == ["W1", "S1"]
    assert [citation.title for citation in resolved] == ["Web Source", "Corpus Source"]


def test_corpus_web_and_food_counters_are_independent() -> None:
    registry = CitationRegistry()
    registry.register_corpus_chunks([make_chunk()])
    registry.register_web_results([make_web_result()])
    registry.register_food_products([make_pet_food_product()])

    resolved = registry.resolve(["S1", "W1", "F1"])
    assert [citation.ref for citation in resolved] == ["S1", "W1", "F1"]
    assert [citation.kind for citation in resolved] == ["corpus", "web", "food"]


# --------------------------------------------------------------------------- #
# CitationRegistry.register_reference_entries
# --------------------------------------------------------------------------- #


def make_reference_entry(title: str = "Chocolate (food, severe)") -> ReferenceEntry:
    """A reference entry standing in for one exact-match lookup row."""
    return ReferenceEntry(
        title=title,
        url="https://example.org/toxic/chocolate",
        body="Chocolate is toxic to dogs.\n- Severity: severe",
    )


def test_extract_finds_single_reference_id() -> None:
    assert extract_referenced_ids("Chocolate is toxic [R1].") == ["R1"]


def test_extract_finds_reference_ids_alongside_every_other_kind() -> None:
    text = "See [S1], [W1], [F1] and [R1]."
    assert extract_referenced_ids(text) == ["S1", "W1", "F1", "R1"]


def test_register_reference_entries_returns_numbered_passage() -> None:
    registry = CitationRegistry()
    passage = registry.register_reference_entries([make_reference_entry()])
    assert passage.startswith("[R1] Chocolate (food, severe)")
    assert "Severity: severe" in passage


def test_register_reference_entries_resolves_to_a_reference_citation() -> None:
    registry = CitationRegistry()
    registry.register_reference_entries([make_reference_entry()])
    citations = registry.resolve(["R1"])
    assert len(citations) == 1
    assert citations[0].ref == "R1"
    assert citations[0].kind == "reference"
    assert citations[0].url == "https://example.org/toxic/chocolate"


def test_register_reference_entries_numbers_multiple_entries() -> None:
    registry = CitationRegistry()
    passage = registry.register_reference_entries(
        [make_reference_entry(), make_reference_entry(title="Xylitol (food, emergency)")]
    )
    assert "[R1]" in passage
    assert "[R2]" in passage


def test_register_reference_entries_continues_ids_across_calls() -> None:
    registry = CitationRegistry()
    first = registry.register_reference_entries([make_reference_entry()])
    second = registry.register_reference_entries([make_reference_entry()])
    assert "[R1]" in first
    assert "[R2]" in second


def test_register_reference_entries_accumulates_retrieved_contexts() -> None:
    registry = CitationRegistry()
    registry.register_reference_entries([make_reference_entry()])
    assert registry.retrieved_contexts == ["Chocolate is toxic to dogs.\n- Severity: severe"]


def test_register_reference_entries_with_no_entries_returns_empty_string() -> None:
    registry = CitationRegistry()
    assert registry.register_reference_entries([]) == ""
