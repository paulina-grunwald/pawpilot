"""Tests for the GET /pets/{id}/tractive/rollups endpoint."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.integrations.tractive.consolidate import GDPR_FILENAMES, GdprExportPayloads


def _build_zip(payloads: GdprExportPayloads) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for field, filename in GDPR_FILENAMES.items():
            archive.writestr(filename, json.dumps(getattr(payloads, field)))
    return buffer.getvalue()


@pytest.fixture
def upload_zip_bytes(sample_gdpr_payloads: GdprExportPayloads) -> bytes:
    return _build_zip(sample_gdpr_payloads)


async def _create_pet_and_ingest(
    client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
    upload_zip_bytes: bytes,
) -> str:
    created = await client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]
    response = await client.post(
        f"/pets/{pet_id}/tractive/ingest",
        files={"file": ("tractive-export.zip", upload_zip_bytes, "application/zip")},
    )
    assert response.status_code == 200, response.text
    assert isinstance(pet_id, str)
    return pet_id


async def test_returns_rollups_oldest_first_with_default_days(
    authenticated_client: AsyncClient,
    upload_zip_bytes: bytes,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet_and_ingest(authenticated_client, valid_pet_payload, upload_zip_bytes)

    response = await authenticated_client.get(f"/pets/{pet_id}/tractive/rollups")
    assert response.status_code == 200
    body = response.json()
    dates = [day["date"] for day in body["daily"]]
    assert dates == ["2024-05-15", "2024-05-16"]
    day_one = body["daily"][0]
    assert day_one["minutes_active"] == 30.0
    assert day_one["minutes_night_sleep"] == 60.0
    assert day_one["heart_rate_mean"] == 62.0
    # Hour keys come back as ints (post-coercion from JSONB string keys).
    hourly = day_one["hourly_minutes_by_category"]
    assert "3" in hourly  # JSON keys serialize as strings over the wire
    assert hourly["3"]["night_sleep"] == 60.0


async def test_returns_empty_list_for_pet_without_rollups(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]
    response = await authenticated_client.get(f"/pets/{pet_id}/tractive/rollups")
    assert response.status_code == 200
    assert response.json() == {"daily": []}


async def test_respects_days_query_parameter(
    authenticated_client: AsyncClient,
    upload_zip_bytes: bytes,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet_and_ingest(authenticated_client, valid_pet_payload, upload_zip_bytes)
    response = await authenticated_client.get(f"/pets/{pet_id}/tractive/rollups?days=1")
    assert response.status_code == 200
    body = response.json()
    assert len(body["daily"]) == 1
    assert body["daily"][0]["date"] == "2024-05-16"  # most-recent-only


async def test_rejects_days_out_of_range(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]
    response = await authenticated_client.get(f"/pets/{pet_id}/tractive/rollups?days=0")
    assert response.status_code == 422
    response = await authenticated_client.get(f"/pets/{pet_id}/tractive/rollups?days=500")
    assert response.status_code == 422


async def test_returns_404_for_other_users_pet(authenticated_client: AsyncClient) -> None:
    stranger_pet_id = uuid.uuid4()
    response = await authenticated_client.get(f"/pets/{stranger_pet_id}/tractive/rollups")
    assert response.status_code == 404
    assert response.json()["detail"] == "PET_NOT_FOUND"


async def test_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(f"/pets/{uuid.uuid4()}/tractive/rollups")
    assert response.status_code == 401
