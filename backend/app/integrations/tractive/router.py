"""HTTP routes for Tractive data ingestion."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.integrations.tractive.gdpr_zip import (
    MAX_GDPR_ZIP_UNCOMPRESSED_BYTES,
    GdprZipError,
    load_gdpr_export_zip,
)
from app.integrations.tractive.read_service import (
    TractiveRollupsResponse,
    fetch_recent_rollups,
)
from app.integrations.tractive.service import IngestResult, TractiveIngestService
from app.pets.models import Pet

MAX_GDPR_ZIP_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB compressed cap on the request
MAX_ROLLUP_QUERY_DAYS = 90

tractive_router = APIRouter(prefix="/pets", tags=["tractive"])


async def _load_owned_pet_or_404(pet_id: uuid.UUID, user: User, session: AsyncSession) -> Pet:
    pet_row = await session.execute(
        select(Pet).where(Pet.id == pet_id, Pet.owner_user_id == user.id)
    )
    pet = pet_row.scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PET_NOT_FOUND")
    return pet


@tractive_router.post(
    "/{pet_id}/tractive/ingest",
    response_model=IngestResult,
    status_code=status.HTTP_200_OK,
)
async def ingest_tractive_export(
    pet_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> IngestResult:
    """Upload a Tractive GDPR-export zip for this pet."""
    pet = await _load_owned_pet_or_404(pet_id, user, session)

    content = await file.read()
    if len(content) > MAX_GDPR_ZIP_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="TRACTIVE_UPLOAD_TOO_LARGE",
        )

    try:
        payloads = load_gdpr_export_zip(content)
    except GdprZipError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"TRACTIVE_INVALID_ZIP: {error}",
        ) from error

    service = TractiveIngestService(session)
    result = await service.ingest_gdpr_export(pet.id, payloads)
    await session.commit()
    return result


@tractive_router.post(
    "/{pet_id}/tractive/reprocess",
    response_model=IngestResult,
    status_code=status.HTTP_200_OK,
)
async def reprocess_tractive_rollups(
    pet_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> IngestResult:
    """Re-run consolidation on the most recent stored raw payloads for this pet.

    Use after consolidation logic changes — avoids re-uploading the GDPR zip.
    """
    pet = await _load_owned_pet_or_404(pet_id, user, session)
    service = TractiveIngestService(session)
    result = await service.reprocess_latest_batch(pet.id)
    await session.commit()
    return result


@tractive_router.get(
    "/{pet_id}/tractive/rollups",
    response_model=TractiveRollupsResponse,
)
async def list_tractive_rollups(
    pet_id: uuid.UUID,
    days: int = Query(default=7, ge=1, le=MAX_ROLLUP_QUERY_DAYS),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> TractiveRollupsResponse:
    """Return the most recent ``days`` rollups for this pet, oldest-first."""
    pet = await _load_owned_pet_or_404(pet_id, user, session)
    return await fetch_recent_rollups(session, pet.id, days)


__all__ = ["MAX_GDPR_ZIP_UNCOMPRESSED_BYTES", "tractive_router"]
