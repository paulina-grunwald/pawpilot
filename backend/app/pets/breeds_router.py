from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

_BREEDS_JSON_PATH = Path(__file__).parent / "breeds.json"


class BreedRead(BaseModel):
    name: str
    group: str | None
    size_category: str | None


@lru_cache(maxsize=1)
def _load_breeds() -> list[BreedRead]:
    with _BREEDS_JSON_PATH.open() as breeds_file:
        payload = json.load(breeds_file)
    return [BreedRead.model_validate(row) for row in payload["breeds"]]


breeds_router = APIRouter(prefix="/breeds", tags=["breeds"])


@breeds_router.get("", response_model=list[BreedRead])
def list_breeds(
    search_query: str | None = Query(default=None, alias="q", max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
) -> list[BreedRead]:
    breeds = _load_breeds()
    if not search_query:
        return breeds[:limit]
    normalized_query = search_query.strip().lower()
    if not normalized_query:
        return breeds[:limit]
    prefix_hits = [breed for breed in breeds if breed.name.lower().startswith(normalized_query)]
    if len(prefix_hits) >= limit:
        return prefix_hits[:limit]
    substring_hits = [
        breed
        for breed in breeds
        if normalized_query in breed.name.lower()
        and not breed.name.lower().startswith(normalized_query)
    ]
    return (prefix_hits + substring_hits)[:limit]
