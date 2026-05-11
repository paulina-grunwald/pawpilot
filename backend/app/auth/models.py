"""SQLAlchemy User model.

Extends fastapi-users' UUID base table with two columns the spec requires:
  * ``reset_token_jti`` — latest issued reset-token JTI; cleared on use.
  * ``created_at`` — UTC timestamp of registration, surfaced in UserRead.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    reset_token_jti: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
