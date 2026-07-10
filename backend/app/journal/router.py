from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.journal.concerns import compute_is_concern
from app.journal.models import JournalEntry
from app.journal.schemas import (
    InvalidCursorError,
    JournalEntryCreate,
    JournalEntryListResponse,
    JournalEntryPayload,
    JournalEntryRead,
    JournalEntryUpdate,
    ListCursor,
)
from app.media.cleanup import delete_media_quietly
from app.media.deps import get_media_storage
from app.media.storage import (
    MIME_BY_EXTENSION,
    MediaStorage,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)
from app.pets.deps import load_owned_pet
from app.pets.models import Pet

JOURNAL_PHOTO_NAMESPACE = "journal"
OCCURRED_AT_FUTURE_TOLERANCE = timedelta(minutes=5)

EntryTypeName = Literal[
    "meal",
    "bathroom",
    "symptom",
    "mood",
    "medication",
    "weight",
    "vet_visit",
    "free_note",
]

journal_router = APIRouter(prefix="/pets/{pet_id}/journal", tags=["journal"])


async def _load_owned_entry(pet: Pet, entry_id: uuid.UUID, session: AsyncSession) -> JournalEntry:
    result = await session.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.pet_id == pet.id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ENTRY_NOT_FOUND")
    return entry


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _clamp_occurred_at(occurred_at: datetime, pet: Pet) -> datetime:
    occurred_at = _ensure_utc(occurred_at)
    now = datetime.now(UTC)
    if occurred_at > now + OCCURRED_AT_FUTURE_TOLERANCE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="OCCURRED_AT_IN_FUTURE",
        )
    birthday_start = datetime.combine(pet.birthday, time.min, tzinfo=UTC)
    if occurred_at < birthday_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="OCCURRED_AT_BEFORE_BIRTHDAY",
        )
    return occurred_at


def _ensure_symptom_has_tags(payload: JournalEntryPayload, tags: list[str]) -> None:
    if payload.entry_type == "symptom" and not tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="SYMPTOM_TAGS_REQUIRED",
        )


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(
    statement: Select[Any],
    *,
    pet_id: uuid.UUID,
    entry_types: list[EntryTypeName] | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
    tags: list[str] | None,
    concerns_only: bool,
    search: str | None,
) -> Select[Any]:
    statement = statement.where(JournalEntry.pet_id == pet_id)
    if entry_types:
        statement = statement.where(JournalEntry.entry_type.in_(entry_types))
    if occurred_from is not None:
        statement = statement.where(JournalEntry.occurred_at >= _ensure_utc(occurred_from))
    if occurred_to is not None:
        statement = statement.where(JournalEntry.occurred_at <= _ensure_utc(occurred_to))
    if tags:
        statement = statement.where(JournalEntry.tags.overlap(tags))
    if concerns_only:
        statement = statement.where(JournalEntry.is_concern.is_(True))
    if search:
        pattern = f"%{_escape_like(search)}%"
        statement = statement.where(
            or_(
                JournalEntry.note.ilike(pattern),
                func.array_to_string(JournalEntry.tags, " ").ilike(pattern),
            )
        )
    return statement


@journal_router.post("", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    pet_id: uuid.UUID,
    body: JournalEntryCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> JournalEntry:
    pet = await load_owned_pet(pet_id, user, session)
    occurred_at = _clamp_occurred_at(body.occurred_at or datetime.now(UTC), pet)
    entry = JournalEntry(
        pet_id=pet.id,
        entry_type=body.payload.entry_type,
        payload=body.payload.model_dump(mode="json"),
        occurred_at=occurred_at,
        note=body.note,
        tags=body.tags,
        is_concern=compute_is_concern(body.payload),
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@journal_router.get("", response_model=JournalEntryListResponse)
async def list_journal_entries(
    pet_id: uuid.UUID,
    entry_type: Annotated[list[EntryTypeName] | None, Query()] = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    tag: Annotated[list[str] | None, Query()] = None,
    concerns_only: bool = False,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> JournalEntryListResponse:
    pet = await load_owned_pet(pet_id, user, session)

    def filtered(statement: Select[Any]) -> Select[Any]:
        return _apply_filters(
            statement,
            pet_id=pet.id,
            entry_types=entry_type,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            tags=tag,
            concerns_only=concerns_only,
            search=search,
        )

    count_statement = filtered(select(func.count()).select_from(JournalEntry))
    total_matching = (await session.execute(count_statement)).scalar_one()

    page_statement = filtered(select(JournalEntry)).order_by(
        JournalEntry.occurred_at.desc(), JournalEntry.id.desc()
    )
    if cursor is not None:
        try:
            decoded = ListCursor.decode(cursor)
        except InvalidCursorError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_CURSOR"
            ) from error
        page_statement = page_statement.where(
            or_(
                JournalEntry.occurred_at < decoded.occurred_at,
                and_(
                    JournalEntry.occurred_at == decoded.occurred_at,
                    JournalEntry.id < decoded.entry_id,
                ),
            )
        )
    page_statement = page_statement.limit(limit + 1)

    rows = list((await session.execute(page_statement)).scalars().all())
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = (
        ListCursor(occurred_at=page[-1].occurred_at, entry_id=page[-1].id).encode()
        if has_more and page
        else None
    )
    return JournalEntryListResponse(
        items=[JournalEntryRead.model_validate(row) for row in page],
        next_cursor=next_cursor,
        total_matching=total_matching,
    )


@journal_router.get("/{entry_id}", response_model=JournalEntryRead)
async def get_journal_entry(
    pet_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> JournalEntry:
    pet = await load_owned_pet(pet_id, user, session)
    return await _load_owned_entry(pet, entry_id, session)


@journal_router.patch("/{entry_id}", response_model=JournalEntryRead)
async def update_journal_entry(
    pet_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: JournalEntryUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> JournalEntry:
    pet = await load_owned_pet(pet_id, user, session)
    entry = await _load_owned_entry(pet, entry_id, session)

    changes = body.model_dump(exclude_unset=True)
    if body.payload is not None:
        if body.payload.entry_type != entry.entry_type:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ENTRY_TYPE_IMMUTABLE")
        entry.payload = body.payload.model_dump(mode="json")
        entry.is_concern = compute_is_concern(body.payload)
    if body.occurred_at is not None:
        entry.occurred_at = _clamp_occurred_at(body.occurred_at, pet)
    if "note" in changes:
        entry.note = body.note
    if body.tags is not None:
        entry.tags = body.tags

    final_payload: JournalEntryPayload = (
        body.payload if body.payload is not None else JournalEntryRead.model_validate(entry).payload
    )
    _ensure_symptom_has_tags(final_payload, entry.tags)

    await session.commit()
    await session.refresh(entry)
    return entry


@journal_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    pet_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> None:
    pet = await load_owned_pet(pet_id, user, session)
    entry = await _load_owned_entry(pet, entry_id, session)
    photo_path = entry.photo_path
    await session.delete(entry)
    await session.commit()
    await delete_media_quietly(media, photo_path)


@journal_router.post("/{entry_id}/photo", response_model=JournalEntryRead)
async def upload_journal_entry_photo(
    pet_id: uuid.UUID,
    entry_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> JournalEntry:
    pet = await load_owned_pet(pet_id, user, session)
    entry = await _load_owned_entry(pet, entry_id, session)

    content_type = file.content_type or ""
    try:
        stored = await media.save(
            namespace=JOURNAL_PHOTO_NAMESPACE,
            subject_id=pet.id,
            content_type=content_type,
            fileobj=file.file,
        )
    except UnsupportedMediaTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="ENTRY_PHOTO_UNSUPPORTED_MEDIA_TYPE",
        ) from error
    except PayloadTooLargeError as error:
        raise HTTPException(status_code=413, detail="ENTRY_PHOTO_TOO_LARGE") from error

    prior_path = entry.photo_path
    entry.photo_path = stored.relative_path
    try:
        await session.commit()
    except Exception:
        # Best-effort so a cleanup error cannot mask the original commit error.
        await delete_media_quietly(media, stored.relative_path)
        raise
    await session.refresh(entry)

    if prior_path and prior_path != stored.relative_path:
        await delete_media_quietly(media, prior_path)

    return entry


@journal_router.get("/{entry_id}/photo")
async def get_journal_entry_photo(
    pet_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> Response:
    pet = await load_owned_pet(pet_id, user, session)
    entry = await _load_owned_entry(pet, entry_id, session)
    if entry.photo_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ENTRY_PHOTO_NOT_FOUND")
    content = await media.read(entry.photo_path)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ENTRY_PHOTO_NOT_FOUND")
    suffix = Path(entry.photo_path).suffix.lower()
    media_type = MIME_BY_EXTENSION.get(suffix, "application/octet-stream")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@journal_router.delete("/{entry_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry_photo(
    pet_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    media: MediaStorage = Depends(get_media_storage),
) -> None:
    pet = await load_owned_pet(pet_id, user, session)
    entry = await _load_owned_entry(pet, entry_id, session)
    prior_path = entry.photo_path
    entry.photo_path = None
    await session.commit()
    await delete_media_quietly(media, prior_path)
