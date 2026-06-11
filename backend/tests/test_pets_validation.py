from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from httpx import AsyncClient

from app.pets import schemas


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
    ancient = (today - relativedelta(years=30)).isoformat()
    response = await authenticated_client.post("/pets", json=valid_pet_payload(birthday=ancient))
    assert response.status_code == 422


def test_validate_birthday_does_not_crash_on_leap_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: when 'today' is Feb 29, computing the earliest allowed
    birthday must not raise — ``today.year - MAX_BIRTHDAY_AGE_YEARS`` is not a
    leap year, so a naive ``date(year, 2, 29)`` would throw and 500 every pet
    create/update that day.
    """
    leap_day = date(2024, 2, 29)
    monkeypatch.setattr(schemas, "_today_utc", lambda: leap_day)

    earliest = leap_day - relativedelta(years=schemas.MAX_BIRTHDAY_AGE_YEARS)
    assert schemas._validate_birthday(earliest) == earliest
    assert schemas._validate_birthday(date(2024, 2, 28)) == date(2024, 2, 28)
    with pytest.raises(ValueError):
        schemas._validate_birthday(earliest - timedelta(days=1))


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
    ancient = (today - relativedelta(years=30)).isoformat()
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


@pytest.mark.parametrize(
    "field",
    ["name", "birthday", "sex", "spayed_neutered", "weight_grams"],
)
async def test_patch_pet_rejects_explicit_null_for_required_field(
    field: str,
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={field: None})
    assert response.status_code == 422, response.text
    assert field in response.text


async def test_patch_pet_allows_explicit_null_to_clear_breed_other(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post(
        "/pets", json=valid_pet_payload(breed_other="Aussie mix")
    )
    pet_id = created.json()["id"]

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"breed_other": None})
    assert response.status_code == 200, response.text
    assert response.json()["breed_other"] is None


async def test_patch_pet_allows_explicit_null_to_clear_notes(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post(
        "/pets", json=valid_pet_payload(notes="Loves frisbee.")
    )
    pet_id = created.json()["id"]

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"notes": None})
    assert response.status_code == 200, response.text
    assert response.json()["notes"] is None
