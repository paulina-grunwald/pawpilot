from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.pets.models import Pet


async def load_owned_pet(pet_id: uuid.UUID, user: User, session: AsyncSession) -> Pet:
    """Load a pet scoped to its owner, raising 404 if it's missing or owned by
    someone else.

    Shared by the pets and tractive routers so per-owner authorization lives in
    exactly one place.
    """
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.owner_user_id == user.id)
    )
    pet = result.scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_NOT_FOUND")
    return pet
