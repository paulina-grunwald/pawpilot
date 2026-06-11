from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ENTRY_TYPES = (
    "meal",
    "bathroom",
    "symptom",
    "mood",
    "medication",
    "weight",
    "vet_visit",
    "free_note",
)


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type in ('meal', 'bathroom', 'symptom', 'mood', "
            "'medication', 'weight', 'vet_visit', 'free_note')",
            name="ck_journal_entries_entry_type_enum",
        ),
        Index(
            "ix_journal_entries_pet_occurred_id",
            "pet_id",
            text("occurred_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_journal_entries_pet_type_occurred",
            "pet_id",
            "entry_type",
            text("occurred_at DESC"),
        ),
        Index(
            "ix_journal_entries_tags",
            "tags",
            postgresql_using="gin",
        ),
        Index(
            "ix_journal_entries_pet_concern_occurred",
            "pet_id",
            text("occurred_at DESC"),
            postgresql_where=text("is_concern"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    is_concern: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
