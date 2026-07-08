"""Markdown/text chunking for ingest.

Pure and dependency-light: takes per-page text and produces ChunkRecord`s using
the same RecursiveCharacterTextSplitter(1000, 200).
Splitting is done *per page* so every chunk maps to exactly one page — the
citation contract's page_start/page_end come for free, and a chunk never
straddles a page boundary.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
_MAX_SECTION_LABEL = 80


class PageText(BaseModel):
    """One page of extracted PDF text."""

    page_number: int
    text: str


class ChunkRecord(BaseModel):
    """A single chunk, ready to embed + upsert."""

    text: str
    page_start: int
    page_end: int
    section: str
    start_index: int
    chunk_index: int


def _first_heading(text: str) -> str:
    """Crude section label: the page's first non-empty line, truncated."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:_MAX_SECTION_LABEL]
    return ""


def chunk_pages(
    pages: list[PageText],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[ChunkRecord]:
    """Split each page into overlapping chunks, carrying page + section metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )

    records: list[ChunkRecord] = []
    chunk_index = 0
    for page in pages:
        if not page.text.strip():
            continue
        section = _first_heading(page.text)
        for document in splitter.create_documents([page.text]):
            records.append(
                ChunkRecord(
                    text=document.page_content,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    section=section,
                    start_index=document.metadata["start_index"],
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
    return records
