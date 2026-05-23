from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from httpx import AsyncClient


async def test_birthday_in_future_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    response = await authenticated_client.post("/pets", json=valid_pet_payload(birthday=tomorrow))
    assert response.status_code == 422
    assert "birthday" in response.text


async def test_weight_below_floor_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await authenticated_client.post("/pets", json=valid_pet_payload(weight_grams=50))
    assert response.status_code == 422


async def test_weight_above_ceiling_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await authenticated_client.post("/pets", json=valid_pet_payload(weight_grams=200000))
    assert response.status_code == 422


async def test_empty_name_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await authenticated_client.post("/pets", json=valid_pet_payload(name=""))
    assert response.status_code == 422


async def test_long_name_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await authenticated_client.post("/pets", json=valid_pet_payload(name="x" * 61))
    assert response.status_code == 422


async def test_invalid_sex_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await authenticated_client.post("/pets", json=valid_pet_payload(sex="unknown"))
    assert response.status_code == 422


async def test_ancient_birthday_rejected(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    today = datetime.now(UTC).date()
    ancient = date(today.year - 30, today.month, today.day).isoformat()
    response = await authenticated_client.post("/pets", json=valid_pet_payload(birthday=ancient))
    assert response.status_code == 422


async def test_patch_pet_rejects_future_birthday(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"birthday": tomorrow})
    assert response.status_code == 422
    assert "birthday" in response.text


async def test_patch_pet_rejects_ancient_birthday(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    today = datetime.now(UTC).date()
    ancient = date(today.year - 30, today.month, today.day).isoformat()
    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"birthday": ancient})
    assert response.status_code == 422


async def test_patch_pet_rejects_weight_below_floor(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"weight_grams": 50})
    assert response.status_code == 422


async def test_patch_pet_empty_payload_is_noop(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    created_body = created.json()
    pet_id = created_body["id"]

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == created_body["name"]
    assert body["weight_grams"] == created_body["weight_grams"]
    assert body["birthday"] == created_body["birthday"]
