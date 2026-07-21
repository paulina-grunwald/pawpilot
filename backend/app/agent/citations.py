"""Citation capture: turn retrieved passages into stable ``[S#]``/``[W#]`` ids.

During a run, each retrieval registers its passages with the `CitationRegistry`,
which assigns sequential ids and formats the passages for the model to read.
After the run, `extract_referenced_ids` finds the ids the model actually cited in
its final answer, and the registry resolves those back to `Citation` objects.
Passages the model never cited are dropped from the answer (they stay in the
LangSmith trace).
"""

from __future__ import annotations

import re

from app.agent.pet_food import PetFoodProduct
from app.agent.schemas import Citation
from app.agent.web_search import WebSearchResult
from app.rag.schemas import RetrievedChunk

_REFERENCE_PATTERN = re.compile(r"\[([SWF]\d+)\]")


def _wrap_untrusted(label: str, body: str) -> str:
    """Fence live third-party tool output so the model reads it as data, not orders.

    Web and pet-food results come from outside our trust boundary and can carry
    injected instructions (indirect prompt injection). Fencing them in a named
    block, paired with the system prompt's untrusted-content rule, marks exactly
    which spans are attacker-influenceable. The corpus is not fenced: it is our
    curated PDF set, and fencing it would also perturb the generation eval's
    retrieved-context baseline for no threat-model gain.
    """
    return f"<untrusted_{label}>\n{body}\n</untrusted_{label}>"


def extract_referenced_ids(text: str) -> list[str]:
    """Return the citation ids referenced in ``text``, in first-seen order."""
    referenced: list[str] = []
    for match in _REFERENCE_PATTERN.finditer(text):
        ref = match.group(1)
        if ref not in referenced:
            referenced.append(ref)
    return referenced


class CitationRegistry:
    """Accumulates citations across a run and formats passages for the model.

    Ids continue across multiple tool calls in the same run (``S1``, ``S2``, …
    for the corpus; ``W1``, ``W2``, … for the web; ``F1``, ``F2``, … for pet
    food), so every referenced id is unambiguous no matter how many times a tool
    ran.
    """

    def __init__(self) -> None:
        self._citations: dict[str, Citation] = {}
        self._corpus_count = 0
        self._web_count = 0
        self._food_count = 0
        self._retrieved_contexts: list[str] = []

    def register_corpus_chunks(self, chunks: list[RetrievedChunk]) -> str:
        """Assign ``[S#]`` ids to chunks and return them as numbered passages."""
        passages: list[str] = []
        for chunk in chunks:
            self._corpus_count += 1
            ref = f"S{self._corpus_count}"
            self._citations[ref] = Citation(
                ref=ref,
                kind="corpus",
                title=chunk.title,
                url=chunk.url,
                source_id=chunk.source_id,
                source_tier=chunk.source_tier,
                page_start=chunk.page_start,
            )
            passages.append(f"[{ref}] {chunk.title} (p.{chunk.page_start})\n{chunk.text}")
            self._retrieved_contexts.append(chunk.text)
        return "\n\n".join(passages)

    def register_web_results(self, results: list[WebSearchResult]) -> str:
        """Assign ``[W#]`` ids to web results and return them as numbered snippets."""
        snippets: list[str] = []
        for result in results:
            self._web_count += 1
            ref = f"W{self._web_count}"
            self._citations[ref] = Citation(
                ref=ref,
                kind="web",
                title=result.title,
                url=result.url,
            )
            snippets.append(f"[{ref}] {result.title} ({result.url})\n{result.content}")
            self._retrieved_contexts.append(result.content)
        if not snippets:
            return ""
        return _wrap_untrusted("web_results", "\n\n".join(snippets))

    def register_food_products(self, products: list[PetFoodProduct]) -> str:
        """Assign ``[F#]`` ids to pet-food products and return them as passages."""
        passages: list[str] = []
        for product in products:
            self._food_count += 1
            ref = f"F{self._food_count}"
            self._citations[ref] = Citation(
                ref=ref,
                kind="food",
                title=product.display_title,
                url=product.url,
            )
            body = product.describe()
            passages.append(f"[{ref}] {product.display_title} ({product.url})\n{body}")
            self._retrieved_contexts.append(body)
        if not passages:
            return ""
        return _wrap_untrusted("food_results", "\n\n".join(passages))

    def resolve(self, referenced_ids: list[str]) -> list[Citation]:
        """Map referenced ids back to citations, ignoring unknown ids, in order."""
        return [self._citations[ref] for ref in referenced_ids if ref in self._citations]

    @property
    def retrieved_contexts(self) -> list[str]:
        """Every passage the model saw this run, corpus and web, in registration order.

        RAGAS generation metrics score the answer against the exact text retrieval
        surfaced, cited or not, so this accumulates raw chunk/result text.
        """
        return list(self._retrieved_contexts)
