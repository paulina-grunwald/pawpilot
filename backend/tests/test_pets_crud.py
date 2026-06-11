from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from dateutil.relativedelta import relativedelta
from httpx import AsyncClient

from app.pets.schemas import _life_stage_from_age


async def test_create_pet_returns_pet_with_derived_fields(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await authenticated_client.post("/pets", json=valid_pet_payload())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Luna"
    assert body["sex"] == "female"
    assert body["spayed_neutered"] is True
    assert body["weight_grams"] == 22000
    assert body["breed_other"] == "Aussie mix"
    assert body["notes"] == "Loves frisbee."
    assert body["photo_path"] is None
    assert isinstance(body["id"], str)
    assert body["age_years"] >= 4
    assert 0 <= body["age_months"] <= 11
    assert body["age_weeks"] >= 200
    assert body["life_stage"] in {"puppy", "adolescent", "adult", "senior"}


async def test_list_pets_returns_only_current_users_pets_newest_first(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    first = await authenticated_client.post("/pets", json=valid_pet_payload(name="Aldo"))
    second = await authenticated_client.post("/pets", json=valid_pet_payload(name="Bee"))
    assert first.status_code == 201 and second.status_code == 201

    response = await authenticated_client.get("/pets")
    assert response.status_code == 200
    body = response.json()
    assert [pet["name"] for pet in body] == ["Bee", "Aldo"]


async def test_list_pets_returns_empty_for_new_user(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.get("/pets")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_pet_by_id_returns_owned_pet(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    response = await authenticated_client.get(f"/pets/{pet_id}")
    assert response.status_code == 200
    assert response.json()["id"] == pet_id


async def test_patch_pet_updates_only_provided_fields(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"weight_grams": 23500})
    assert response.status_code == 200
    body = response.json()
    assert body["weight_grams"] == 23500
    assert body["name"] == "Luna"


async def test_delete_pet_returns_204_then_404_on_refetch(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    delete_response = await authenticated_client.delete(f"/pets/{pet_id}")
    assert delete_response.status_code == 204

    refetch = await authenticated_client.get(f"/pets/{pet_id}")
    assert refetch.status_code == 404


async def test_age_years_zero_for_pet_under_one(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    today = datetime.now(UTC).date()
    six_months_ago = today - relativedelta(months=6)
    response = await authenticated_client.post(
        "/pets", json=valid_pet_payload(birthday=str(six_months_ago))
    )
    assert response.status_code == 201
    body = response.json()
    assert body["age_years"] == 0
    assert body["life_stage"] == "puppy"


@pytest.mark.parametrize(
    ("years", "months", "expected"),
    [
        (0, 0, "puppy"),
        (0, 11, "puppy"),
        (1, 0, "adolescent"),
        (1, 11, "adolescent"),
        (2, 0, "adult"),
        (7, 11, "adult"),
        (8, 0, "senior"),
        (20, 6, "senior"),
    ],
)
def test_life_stage_from_age_covers_all_branches(years: int, months: int, expected: str) -> None:
    assert _life_stage_from_age(years, months) == expected
