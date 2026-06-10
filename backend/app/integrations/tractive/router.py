"""HTTP routes for Tractive data ingestion."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.integrations.tractive.consolidate import MalformedTractivePayloadError
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
from app.pets.deps import load_owned_pet

MAX_GDPR_ZIP_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB compressed cap on the request
MAX_ROLLUP_QUERY_DAYS = 90
_UPLOAD_CHUNK_BYTES = 64 * 1024

tractive_router = APIRouter(prefix="/pets", tags=["tractive"])


async def _read_upload_within_cap(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in bounded chunks, raising 413 as soon as the running
    total exceeds ``max_bytes``.

    Unlike ``await file.read()``, this never fully buffers an oversized body in
    memory — it stops at the first chunk that crosses the cap.
    """
    chunks: list[bytes] = []
    total_bytes = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="TRACTIVE_UPLOAD_TOO_LARGE",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _invalid_zip_error(error: Exception) -> HTTPException:
    """The 400 that an unreadable or structurally-invalid Tractive export maps to."""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"TRACTIVE_INVALID_ZIP: {error}",
    )


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
    pet = await load_owned_pet(pet_id, user, session)

    content = await _read_upload_within_cap(file, MAX_GDPR_ZIP_UPLOAD_BYTES)

    try:
        payloads = load_gdpr_export_zip(content)
    except GdprZipError as error:
        raise _invalid_zip_error(error) from error

    service = TractiveIngestService(session)
    try:
        result = await service.ingest_gdpr_export(pet.id, payloads)
    except MalformedTractivePayloadError as error:
        raise _invalid_zip_error(error) from error
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
    pet = await load_owned_pet(pet_id, user, session)
    service = TractiveIngestService(session)
    try:
        result = await service.reprocess_latest_batch(pet.id)
    except MalformedTractivePayloadError as error:
        raise _invalid_zip_error(error) from error
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
    pet = await load_owned_pet(pet_id, user, session)
    return await fetch_recent_rollups(session, pet.id, days)


__all__ = ["MAX_GDPR_ZIP_UNCOMPRESSED_BYTES", "tractive_router"]
