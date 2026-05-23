from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.media.deps import get_media_storage
from app.media.storage import (
    MediaStorage,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from app.pets.models import Pet
from app.pets.schemas import PetCreate, PetRead, PetUpdate

PET_PHOTO_NAMESPACE = "pets"

pets_router = APIRouter(prefix="/pets", tags=["pets"])


async def _load_owned_pet(pet_id: uuid.UUID, user: User, session: AsyncSession) -> Pet:
    result = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.owner_user_id == user.id)
    )
    pet = result.scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_NOT_FOUND")
    return pet


@pets_router.get("", response_model=list[PetRead])
async def list_pets(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[Pet]:
    result = await session.execute(
        select(Pet).where(Pet.owner_user_id == user.id).order_by(Pet.created_at.desc())
    )
    return list(result.scalars().all())


@pets_router.post("", response_model=PetRead, status_code=status.HTTP_201_CREATED)
async def create_pet(
    payload: PetCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Pet:
    pet = Pet(
        owner_user_id=user.id,
        name=payload.name,
        breed_other=payload.breed_other,
        birthday=payload.birthday,
        sex=payload.sex,
        spayed_neutered=payload.spayed_neutered,
        weight_grams=payload.weight_grams,
        notes=payload.notes,
    )
    session.add(pet)
    await session.commit()
    await session.refresh(pet)
    return pet


@pets_router.get("/{pet_id}", response_model=PetRead)
async def get_pet(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Pet:
    return await _load_owned_pet(pet_id, user, session)


@pets_router.patch("/{pet_id}", response_model=PetRead)
async def update_pet(
    pet_id: uuid.UUID,
    payload: PetUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Pet:
    pet = await _load_owned_pet(pet_id, user, session)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(pet, field, value)
    await session.commit()
    await session.refresh(pet)
    return pet


@pets_router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> None:
    pet = await _load_owned_pet(pet_id, user, session)
    owner_dir_id = pet.id
    await session.delete(pet)
    await session.commit()
    media.delete_owner_dir(PET_PHOTO_NAMESPACE, owner_dir_id)


@pets_router.post("/{pet_id}/photo", response_model=PetRead)
async def upload_pet_photo(
    pet_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> Pet:
    pet = await _load_owned_pet(pet_id, user, session)

    content_type = file.content_type or ""
    try:
        stored = media.save(
            namespace=PET_PHOTO_NAMESPACE,
            owner_id=pet.id,
            content_type=content_type,
            fileobj=file.file,
        )
    except UnsupportedMediaTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="PET_PHOTO_UNSUPPORTED_MEDIA_TYPE",
        ) from error
    except PayloadTooLargeError as error:
        raise HTTPException(
            status_code=413,
            detail="PET_PHOTO_TOO_LARGE",
        ) from error

    prior_path = pet.photo_path
    pet.photo_path = stored.relative_path
    await session.commit()
    await session.refresh(pet)

    if prior_path and prior_path != stored.relative_path:
        media.delete(prior_path)

    return pet


@pets_router.delete("/{pet_id}/photo", response_model=PetRead)
async def delete_pet_photo(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> Pet:
    pet = await _load_owned_pet(pet_id, user, session)
    prior_path = pet.photo_path
    pet.photo_path = None
    await session.commit()
    await session.refresh(pet)
    media.delete(prior_path)
    return pet
