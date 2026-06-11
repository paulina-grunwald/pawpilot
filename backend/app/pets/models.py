from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint(
            "weight_grams >= 100 AND weight_grams <= 120000",
            name="ck_pets_weight_grams_range",
        ),
        CheckConstraint(
            "sex in ('male', 'female')",
            name="ck_pets_sex_enum",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    breed_other: Mapped[str | None] = mapped_column(String(80), nullable=True)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(8), nullable=False)
    spayed_neutered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
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
