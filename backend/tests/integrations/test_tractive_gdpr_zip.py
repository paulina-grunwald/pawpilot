"""Tests for the Tractive GDPR-export zip loader."""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from app.integrations.tractive.consolidate import GDPR_FILENAMES, GdprExportPayloads
from app.integrations.tractive.gdpr_zip import GdprZipError, load_gdpr_export_zip


def _zip_with_all_files(payloads: GdprExportPayloads, *, prefix: str = "") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            archive.writestr(f"{prefix}{filename}", json.dumps(getattr(payloads, field)))
    return buffer.getvalue()


def test_loads_export_with_flat_layout(sample_gdpr_payloads: GdprExportPayloads) -> None:
    loaded = load_gdpr_export_zip(_zip_with_all_files(sample_gdpr_payloads))
    assert len(loaded.activity_data) == 2
    assert len(loaded.position_reports) == 3


def test_loads_export_with_top_level_folder(sample_gdpr_payloads: GdprExportPayloads) -> None:
    loaded = load_gdpr_export_zip(
        _zip_with_all_files(sample_gdpr_payloads, prefix="tractive-export-12345/")
    )
    assert len(loaded.activity_data) == 2


def test_raises_on_invalid_zip_bytes() -> None:
    with pytest.raises(GdprZipError, match="not a valid zip"):
        load_gdpr_export_zip(b"not a zip")


def test_raises_when_required_file_missing(sample_gdpr_payloads: GdprExportPayloads) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            if filename == "hardware_reports.json":
                continue
            archive.writestr(filename, json.dumps(getattr(sample_gdpr_payloads, field)))

    with pytest.raises(GdprZipError, match=r"hardware_reports\.json"):
        load_gdpr_export_zip(buffer.getvalue())


def test_raises_when_member_has_malformed_json(
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            if filename == "activity_data.json":
                archive.writestr(filename, "{not json")
            else:
                archive.writestr(filename, json.dumps(getattr(sample_gdpr_payloads, field)))

    with pytest.raises(GdprZipError, match="not valid JSON"):
        load_gdpr_export_zip(buffer.getvalue())


def test_rejects_zip_with_excessive_uncompressed_size(
    monkeypatch: pytest.MonkeyPatch, sample_gdpr_payloads: GdprExportPayloads
) -> None:
    monkeypatch.setattr("app.integrations.tractive.gdpr_zip.MAX_GDPR_ZIP_UNCOMPRESSED_BYTES", 10)
    with pytest.raises(GdprZipError, match="exceed"):
        load_gdpr_export_zip(_zip_with_all_files(sample_gdpr_payloads))


def test_raises_on_duplicate_required_file(sample_gdpr_payloads: GdprExportPayloads) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            archive.writestr(f"a/{filename}", json.dumps(getattr(sample_gdpr_payloads, field)))
        # A second copy of one required file in a different folder — ambiguous.
        archive.writestr("b/activity_data.json", json.dumps(sample_gdpr_payloads.activity_data))

    with pytest.raises(GdprZipError, match="duplicate"):
        load_gdpr_export_zip(buffer.getvalue())
