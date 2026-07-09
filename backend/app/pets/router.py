from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.journal.router import JOURNAL_PHOTO_NAMESPACE
from app.media.deps import get_media_storage
from app.media.storage import (
    MIME_BY_EXTENSION,
    MediaStorage,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from app.pets.deps import load_owned_pet
from app.pets.models import Pet
from app.pets.schemas import PetCreate, PetRead, PetUpdate

PET_PHOTO_NAMESPACE = "pets"

pets_router = APIRouter(prefix="/pets", tags=["pets"])


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
    return await load_owned_pet(pet_id, user, session)


@pets_router.patch("/{pet_id}", response_model=PetRead)
async def update_pet(
    pet_id: uuid.UUID,
    payload: PetUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Pet:
    pet = await load_owned_pet(pet_id, user, session)
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
    pet = await load_owned_pet(pet_id, user, session)
    owner_dir_id = pet.id

    await session.delete(pet)
    await session.commit()
    await media.delete_owner_dir(PET_PHOTO_NAMESPACE, owner_dir_id)
    await media.delete_owner_dir(JOURNAL_PHOTO_NAMESPACE, owner_dir_id)


@pets_router.get("/{pet_id}/photo")
async def get_pet_photo(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> Response:
    """Stream this pet's photo, scoped to the authenticated owner.

    Replaces the previous public ``/media`` static mount so a pet photo is only
    reachable by its owner — matching the per-owner authz on every other pet
    route. The ``?v=`` cache-buster carried on ``PetRead.photo_url`` is an
    ignored query param here.
    """
    pet = await load_owned_pet(pet_id, user, session)
    if pet.photo_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_PHOTO_NOT_FOUND")
    content = await media.read(pet.photo_path)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_PHOTO_NOT_FOUND")
    suffix = Path(pet.photo_path).suffix.lower()
    media_type = MIME_BY_EXTENSION.get(suffix, "application/octet-stream")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@pets_router.post("/{pet_id}/photo", response_model=PetRead)
async def upload_pet_photo(
    pet_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> Pet:
    pet = await load_owned_pet(pet_id, user, session)

    content_type = file.content_type or ""
    try:
        stored = await media.save(
            namespace=PET_PHOTO_NAMESPACE,
            subject_id=pet.id,
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
    try:
        await session.commit()
    except Exception:
        # Roll back the stored object so a commit failure does not leak the
        # freshly written file (DB still points at prior_path, which is fine).
        await media.delete(stored.relative_path)
        raise
    await session.refresh(pet)

    if prior_path and prior_path != stored.relative_path:
        await media.delete(prior_path)

    return pet


@pets_router.delete("/{pet_id}/photo", response_model=PetRead)
async def delete_pet_photo(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> Pet:
    pet = await load_owned_pet(pet_id, user, session)
    prior_path = pet.photo_path
    pet.photo_path = None
    await session.commit()
    await session.refresh(pet)
    # MediaStorage.delete is a no-op when prior_path is None or missing.
    await media.delete(prior_path)
    return pet
