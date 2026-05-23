from __future__ import annotations

from httpx import AsyncClient


async def test_list_breeds_no_query_returns_default_page(client: AsyncClient) -> None:
    response = await client.get("/breeds")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 20
    assert all("name" in breed and "size_category" in breed for breed in body)


async def test_list_breeds_respects_limit(client: AsyncClient) -> None:
    response = await client.get("/breeds", params={"limit": 5})
    assert response.status_code == 200
    assert len(response.json()) == 5


async def test_list_breeds_clamps_limit_above_max(client: AsyncClient) -> None:
    response = await client.get("/breeds", params={"limit": 999})
    assert response.status_code == 422


async def test_list_breeds_prefix_match_case_insensitive(client: AsyncClient) -> None:
    response = await client.get("/breeds", params={"q": "aus"})
    assert response.status_code == 200
    names = [breed["name"] for breed in response.json()]
    assert "Australian Shepherd" in names
    assert "Australian Cattle Dog" in names
    assert "Australian Terrier" in names


async def test_list_breeds_falls_back_to_substring(client: AsyncClient) -> None:
    response = await client.get("/breeds", params={"q": "shepherd"})
    assert response.status_code == 200
    names = [breed["name"] for breed in response.json()]
    assert any("Shepherd" in name for name in names)


async def test_mixed_unknown_is_first_breed(client: AsyncClient) -> None:
    response = await client.get("/breeds", params={"limit": 1})
    assert response.json()[0]["name"] == "Mixed / unknown"


async def test_list_breeds_whitespace_query_returns_default_page(
    client: AsyncClient,
) -> None:
    response = await client.get("/breeds", params={"q": "   "})
    assert response.status_code == 200
    assert len(response.json()) == 20


async def test_list_breeds_no_auth_required(client: AsyncClient) -> None:
    response = await client.get("/breeds")
    assert response.status_code == 200
