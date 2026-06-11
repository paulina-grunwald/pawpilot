from __future__ import annotations

from collections.abc import Callable

from httpx import AsyncClient

EntryBuilder = Callable[..., dict[str, object]]


async def _login_as_other_user(client: AsyncClient) -> None:
    credentials = {"email": "mallory@example.com", "password": "another-strong-pass"}
    register = await client.post("/auth/register", json=credentials)
    assert register.status_code == 201, register.text
    client.cookies.clear()
    login = await client.post(
        "/auth/login",
        data={"username": credentials["email"], "password": credentials["password"]},
    )
    assert login.status_code == 204, login.text


async def test_journal_routes_require_authentication(
    client: AsyncClient,
    valid_journal_entry: EntryBuilder,
) -> None:
    pet_path = "/pets/00000000-0000-0000-0000-000000000000/journal"
    entry_path = f"{pet_path}/00000000-0000-0000-0000-000000000001"

    assert (await client.post(pet_path, json=valid_journal_entry())).status_code == 401
    assert (await client.get(pet_path)).status_code == 401
    assert (await client.get(entry_path)).status_code == 401
    assert (await client.patch(entry_path, json={"note": "x"})).status_code == 401
    assert (await client.delete(entry_path)).status_code == 401
    assert (await client.delete(f"{entry_path}/photo")).status_code == 401


async def test_other_users_pet_journal_is_404(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    await _login_as_other_user(authenticated_client)

    list_response = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal")
    get_response = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal/{entry_id}")
    patch_response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}", json={"note": "hijack"}
    )
    delete_response = await authenticated_client.delete(
        f"/pets/{journal_pet['id']}/journal/{entry_id}"
    )

    for response in (list_response, get_response, patch_response, delete_response):
        assert response.status_code == 404
        assert response.json()["detail"] == "PET_NOT_FOUND"


async def test_entry_from_another_pet_is_404(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
    valid_journal_entry: EntryBuilder,
) -> None:
    first_pet = (await authenticated_client.post("/pets", json=valid_pet_payload())).json()
    second_pet = (
        await authenticated_client.post("/pets", json=valid_pet_payload(name="Bo"))
    ).json()
    created = await authenticated_client.post(
        f"/pets/{first_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    response = await authenticated_client.get(f"/pets/{second_pet['id']}/journal/{entry_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "ENTRY_NOT_FOUND"
