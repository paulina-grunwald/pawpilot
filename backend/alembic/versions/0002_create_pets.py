"""Create pets table.

Revision ID: 0002_create_pets
Revises: 0001_users
Create Date: 2026-05-22

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID

from alembic import op

revision: str = "0002_create_pets"
down_revision: str | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pets",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("owner_user_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("breed_other", sa.String(length=80), nullable=True),
        sa.Column("birthday", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(length=8), nullable=False),
        sa.Column("spayed_neutered", sa.Boolean(), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("photo_path", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "weight_grams >= 100 AND weight_grams <= 120000",
            name="ck_pets_weight_grams_range",
        ),
        sa.CheckConstraint(
            "sex in ('male', 'female')",
            name="ck_pets_sex_enum",
        ),
    )
    op.create_index("ix_pets_owner_user_id", "pets", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_pets_owner_user_id", table_name="pets")
    op.drop_table("pets")
