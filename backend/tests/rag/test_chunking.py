from __future__ import annotations

from app.rag.chunking import ChunkRecord, PageText, chunk_pages


def test_short_page_is_a_single_chunk() -> None:
    pages = [PageText(page_number=1, text="Core vaccines protect against disease.")]
    records = chunk_pages(pages)
    assert len(records) == 1
    assert records[0].text == "Core vaccines protect against disease."
    assert records[0].page_start == 1
    assert records[0].page_end == 1
    assert records[0].chunk_index == 0


def test_long_page_splits_into_multiple_chunks() -> None:
    text = " ".join(f"word{index}" for index in range(400))
    records = chunk_pages([PageText(page_number=3, text=text)], chunk_size=200, chunk_overlap=40)
    assert len(records) > 1
    assert all(record.page_start == 3 for record in records)
    # chunk_index is globally sequential
    assert [record.chunk_index for record in records] == list(range(len(records)))


def test_chunks_overlap() -> None:
    text = " ".join(f"token{index}" for index in range(200))
    records = chunk_pages([PageText(page_number=1, text=text)], chunk_size=120, chunk_overlap=40)
    assert len(records) >= 2
    # With overlap, the end of one chunk reappears at the start of the next.
    first_tail = records[0].text.split()[-1]
    assert first_tail in records[1].text


def test_chunk_index_is_sequential_across_pages() -> None:
    pages = [
        PageText(page_number=1, text="alpha " * 100),
        PageText(page_number=2, text="bravo " * 100),
    ]
    records = chunk_pages(pages, chunk_size=150, chunk_overlap=30)
    assert [record.chunk_index for record in records] == list(range(len(records)))
    page_numbers = {record.page_start for record in records}
    assert page_numbers == {1, 2}


def test_blank_pages_are_skipped() -> None:
    pages = [
        PageText(page_number=1, text="   \n  \n "),
        PageText(page_number=2, text="Real content here."),
    ]
    records = chunk_pages(pages)
    assert len(records) == 1
    assert records[0].page_start == 2


def test_section_label_is_first_nonempty_line() -> None:
    text = "\n\nGastrointestinal Disease\nVomiting and diarrhea are common signs."
    records = chunk_pages([PageText(page_number=5, text=text)])
    assert records[0].section == "Gastrointestinal Disease"


def test_no_heading_yields_empty_section() -> None:
    records = chunk_pages([PageText(page_number=1, text="single line no newline")])
    assert records[0].section == "single line no newline"


def test_single_long_paragraph_without_newlines_splits() -> None:
    text = "a" * 5000
    records = chunk_pages([PageText(page_number=1, text=text)], chunk_size=500, chunk_overlap=50)
    assert len(records) > 1
    assert all(isinstance(record, ChunkRecord) for record in records)
    assert all(len(record.text) <= 500 for record in records)
