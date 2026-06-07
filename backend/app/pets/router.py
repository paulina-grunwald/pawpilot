from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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

# Map stored photo extensions back to a response content-type for the
# authenticated photo-serving route. Mirrors media.storage.MIME_EXTENSIONS.
_PHOTO_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

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

    media.delete_owner_dir(PET_PHOTO_NAMESPACE, owner_dir_id)
    await session.delete(pet)
    await session.commit()


@pets_router.get("/{pet_id}/photo")
async def get_pet_photo(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> FileResponse:
    """Stream this pet's photo, scoped to the authenticated owner.

    Replaces the previous public ``/media`` static mount so a pet photo is only
    reachable by its owner — matching the per-owner authz on every other pet
    route. The ``?v=`` cache-buster carried on ``PetRead.photo_url`` is an
    ignored query param here.
    """
    pet = await _load_owned_pet(pet_id, user, session)
    if pet.photo_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_PHOTO_NOT_FOUND")
    absolute_path = media.resolve_within_root(pet.photo_path)
    if absolute_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_PHOTO_NOT_FOUND")
    media_type = _PHOTO_MEDIA_TYPES.get(absolute_path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        absolute_path,
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
    try:
        await session.commit()
    except Exception:
        # Roll back the on-disk write so a commit failure does not leak the
        # freshly written file (DB still points at prior_path, which is fine).
        media.delete(stored.relative_path)
        raise
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
    # Delete the file before committing. If unlink raises, the commit never
    # happens and the DB still references the file — consistent on retry.
    # MediaStorage.delete is a no-op when prior_path is None or missing.
    media.delete(prior_path)
    pet.photo_path = None
    await session.commit()
    await session.refresh(pet)
    return pet
