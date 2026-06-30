from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.rag.manifest import (
    CorpusSource,
    default_corpus_dir,
    load_manifest,
    resolve_source_tier,
)
from app.rag.schemas import SourceTier


def make_source(
    source_id: str = "study-1",
    title: str = "A Retrospective Study",
    organization: str = "Frontiers in Veterinary Science",
    lane: str | None = None,
    source_tier: SourceTier | None = None,
) -> CorpusSource:
    return CorpusSource(
        source_id=source_id,
        title=title,
        organization=organization,
        year=2024,
        url="https://example.org/doc.pdf",
        file=f"{source_id}.pdf",
        lane=lane,
        source_tier=source_tier,
    )


def test_explicit_tier_wins_over_heuristic() -> None:
    source = make_source(organization="Frontiers in Veterinary Science", source_tier="guideline")
    assert resolve_source_tier(source) == "guideline"


def test_breed_tier_from_source_id_prefix() -> None:
    assert resolve_source_tier(make_source(source_id="breed-aussie-mdr1")) == "breed"


def test_breed_tier_from_lane() -> None:
    assert resolve_source_tier(make_source(lane="breed")) == "breed"


def test_consensus_tier_from_acvim_org() -> None:
    source = make_source(organization="Journal of Veterinary Internal Medicine (ACVIM)")
    assert resolve_source_tier(source) == "consensus"


def test_consensus_tier_from_task_force_org() -> None:
    source = make_source(organization="International Veterinary Epilepsy Task Force")
    assert resolve_source_tier(source) == "consensus"


def test_consensus_tier_from_title() -> None:
    source = make_source(title="ACVIM Consensus Statement on Something", organization="Wiley")
    assert resolve_source_tier(source) == "consensus"


def test_guideline_tier_from_org_marker() -> None:
    assert resolve_source_tier(make_source(organization="WSAVA")) == "guideline"
    assert resolve_source_tier(make_source(organization="AAHA")) == "guideline"


def test_guideline_tier_from_title_toolkit() -> None:
    source = make_source(title="Global Nutrition Toolkit", organization="Some Body")
    assert resolve_source_tier(source) == "guideline"


def test_food_tier_from_lane() -> None:
    assert resolve_source_tier(make_source(lane="food")) == "food"


def test_primary_research_is_the_fallback() -> None:
    assert resolve_source_tier(make_source(organization="PLoS ONE")) == "primary_research"


def test_load_manifest_parses_rows(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = [
        {
            "source_id": "wsava-vaccination-2024",
            "title": "Vaccination Guidelines",
            "organization": "WSAVA",
            "year": 2024,
            "url": "https://example.org/a.pdf",
            "file": "a.pdf",
            "pages": 40,
        },
        {
            "source_id": "frontiers-study",
            "title": "A Study",
            "organization": "Frontiers in Veterinary Science",
            "year": 2023,
            "url": "https://example.org/b.pdf",
            "file": "b.pdf",
        },
    ]
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(json.dumps({"sources": rows}), encoding="utf-8")

    sources = load_manifest(manifest_path)

    assert [s.source_id for s in sources] == ["wsava-vaccination-2024", "frontiers-study"]
    assert resolve_source_tier(sources[0]) == "guideline"
    assert resolve_source_tier(sources[1]) == "primary_research"


def test_load_manifest_accepts_bare_list(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = [
        {
            "source_id": "only",
            "title": "T",
            "organization": "Org",
            "year": 2020,
            "url": "https://x",
            "file": "only.pdf",
        }
    ]
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(json.dumps(rows), encoding="utf-8")
    assert len(load_manifest(manifest_path)) == 1


def test_load_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    row: dict[str, object] = {
        "source_id": "dup",
        "title": "T",
        "organization": "Org",
        "year": 2020,
        "url": "https://x",
        "file": "dup.pdf",
    }
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(json.dumps({"sources": [row, row]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate source_id"):
        load_manifest(manifest_path)


_REAL_MANIFEST = default_corpus_dir() / "sources.json"


@pytest.mark.skipif(not _REAL_MANIFEST.exists(), reason="corpus is gitignored / not present")
def test_real_manifest_loads_and_all_tiers_resolve() -> None:
    sources = load_manifest()
    assert len(sources) >= 200
    valid: set[SourceTier] = {"guideline", "consensus", "primary_research", "breed", "food"}
    assert {resolve_source_tier(source) for source in sources} <= valid
    assert len({source.source_id for source in sources}) == len(sources)
