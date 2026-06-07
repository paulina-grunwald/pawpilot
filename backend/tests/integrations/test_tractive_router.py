"""Tests for the POST /pets/{id}/tractive/ingest endpoint."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.integrations.tractive.consolidate import GDPR_FILENAMES, GdprExportPayloads


def _build_zip(payloads: GdprExportPayloads, *, prefix: str = "tractive-export/") -> bytes:
    """Pack a payload set into an in-memory zip mirroring Tractive's layout."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            archive.writestr(f"{prefix}{filename}", json.dumps(getattr(payloads, field)))
    return buffer.getvalue()


@pytest.fixture
def upload_zip_bytes(sample_gdpr_payloads: GdprExportPayloads) -> bytes:
    return _build_zip(sample_gdpr_payloads)


async def _create_pet(
    client: AsyncClient, valid_pet_payload: Callable[..., dict[str, object]]
) -> str:
    response = await client.post("/pets", json=valid_pet_payload())
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    pet_id = body["id"]
    assert isinstance(pet_id, str)
    return pet_id


async def test_ingest_endpoint_returns_summary_for_valid_zip(
    authenticated_client: AsyncClient,
    upload_zip_bytes: bytes,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)

    response = await authenticated_client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("tractive-export.zip", upload_zip_bytes, "application/zip")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rollups_upserted"] == 2
    assert body["raw_payloads_stored"] == 5
    assert body["date_range_start"] == "2024-05-15"
    assert body["date_range_end"] == "2024-05-16"
    uuid.UUID(body["ingest_batch_id"])  # parseable uuid


async def test_ingest_endpoint_rejects_non_zip_payload(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    response = await authenticated_client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("not-a-zip.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "TRACTIVE_INVALID_ZIP" in response.json()["detail"]


async def test_ingest_endpoint_rejects_zip_missing_required_file(
    authenticated_client: AsyncClient,
    sample_gdpr_payloads: GdprExportPayloads,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)

    # Build a zip missing position_reports.json.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            if filename == "position_reports.json":
                continue
            archive.writestr(filename, json.dumps(getattr(sample_gdpr_payloads, field)))

    response = await authenticated_client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("broken.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "position_reports.json" in response.json()["detail"]


async def test_ingest_endpoint_rejects_oversize_upload(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)

    monkeypatch.setattr(
        "app.integrations.tractive.router.MAX_GDPR_ZIP_UPLOAD_BYTES",
        10,
    )

    response = await authenticated_client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("oversize.zip", b"x" * 50, "application/zip")},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "TRACTIVE_UPLOAD_TOO_LARGE"


async def test_ingest_endpoint_returns_404_for_other_users_pet(
    authenticated_client: AsyncClient,
    upload_zip_bytes: bytes,
) -> None:
    stranger_pet_id = uuid.uuid4()
    response = await authenticated_client.post(
        f"/pets/{stranger_pet_id}/tractive/ingest",
        files={"file": ("tractive-export.zip", upload_zip_bytes, "application/zip")},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "PET_NOT_FOUND"


async def test_ingest_endpoint_requires_authentication(
    client: AsyncClient, upload_zip_bytes: bytes
) -> None:
    pet_id = uuid.uuid4()
    response = await client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("tractive-export.zip", upload_zip_bytes, "application/zip")},
    )
    assert response.status_code == 401


async def test_reprocess_endpoint_replays_latest_raw_batch(
    authenticated_client: AsyncClient,
    upload_zip_bytes: bytes,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]
    ingest = await authenticated_client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("tractive-export.zip", upload_zip_bytes, "application/zip")},
    )
    assert ingest.status_code == 200

    response = await authenticated_client.post(f"/pets/{pet_id}/tractive/reprocess")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rollups_upserted"] == 2
    assert body["raw_payloads_stored"] == 0  # reprocess reads, doesn't write blobs
    assert body["date_range_start"] == "2024-05-15"
    assert body["date_range_end"] == "2024-05-16"


async def test_reprocess_endpoint_returns_zero_when_no_raw_batch_exists(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]
    response = await authenticated_client.post(f"/pets/{pet_id}/tractive/reprocess")
    assert response.status_code == 200
    body = response.json()
    assert body["rollups_upserted"] == 0
    assert body["date_range_start"] is None


async def test_reprocess_endpoint_rejects_other_users_pet(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.post(f"/pets/{uuid.uuid4()}/tractive/reprocess")
    assert response.status_code == 404
