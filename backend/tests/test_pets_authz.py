from __future__ import annotations

from collections.abc import Callable

from httpx import AsyncClient


async def _login_as_other_user(client: AsyncClient, email: str, password: str) -> None:
    register = await client.post("/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201, register.text
    client.cookies.clear()
    login = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 204, login.text


async def test_list_pets_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/pets")
    assert response.status_code == 401


async def test_create_pet_unauthenticated_returns_401(
    client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    response = await client.post("/pets", json=valid_pet_payload())
    assert response.status_code == 401


async def test_patch_pet_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.patch(
        "/pets/00000000-0000-0000-0000-000000000000",
        json={"name": "Rex"},
    )
    assert response.status_code == 401


async def test_delete_pet_photo_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.delete("/pets/00000000-0000-0000-0000-000000000000/photo")
    assert response.status_code == 401


async def test_get_other_users_pet_returns_404_not_403(
    authenticated_client: AsyncClient,
    client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    await _login_as_other_user(authenticated_client, "bob@example.com", "another-strong-pass")

    response = await authenticated_client.get(f"/pets/{pet_id}")
    assert response.status_code == 404


async def test_patch_other_users_pet_returns_404(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    await _login_as_other_user(authenticated_client, "diana@example.com", "another-strong-pass")

    response = await authenticated_client.patch(f"/pets/{pet_id}", json={"name": "Hijacked"})
    assert response.status_code == 404


async def test_delete_other_users_pet_returns_404(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    await _login_as_other_user(authenticated_client, "carol@example.com", "another-strong-pass")

    response = await authenticated_client.delete(f"/pets/{pet_id}")
    assert response.status_code == 404


async def test_delete_other_users_pet_photo_returns_404(
    authenticated_client: AsyncClient,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    await _login_as_other_user(authenticated_client, "eve@example.com", "another-strong-pass")

    response = await authenticated_client.delete(f"/pets/{pet_id}/photo")
    assert response.status_code == 404
