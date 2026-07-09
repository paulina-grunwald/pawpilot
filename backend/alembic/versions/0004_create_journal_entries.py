"""Create journal_entries table.

Revision ID: 0004_create_journal_entries
Revises: 0003_create_tractive_tables
Create Date: 2026-06-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0004_create_journal_entries"
down_revision: str | None = "0003_create_tractive_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("pet_id", GUID(), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column(
            "tags",
            sa.ARRAY(sa.String(length=50)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "is_concern",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "entry_type in ('meal', 'bathroom', 'symptom', 'mood', "
            "'medication', 'weight', 'vet_visit', 'free_note')",
            name="ck_journal_entries_entry_type_enum",
        ),
    )
    op.create_index("ix_journal_entries_pet_id", "journal_entries", ["pet_id"])
    op.create_index("ix_journal_entries_occurred_at", "journal_entries", ["occurred_at"])
    op.create_index(
        "ix_journal_entries_pet_occurred_id",
        "journal_entries",
        ["pet_id", sa.text("occurred_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_journal_entries_pet_type_occurred",
        "journal_entries",
        ["pet_id", "entry_type", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_journal_entries_tags",
        "journal_entries",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_journal_entries_pet_concern_occurred",
        "journal_entries",
        ["pet_id", sa.text("occurred_at DESC")],
        postgresql_where=sa.text("is_concern"),
    )


def downgrade() -> None:
    op.drop_index("ix_journal_entries_pet_concern_occurred", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tags", table_name="journal_entries")
    op.drop_index("ix_journal_entries_pet_type_occurred", table_name="journal_entries")
    op.drop_index("ix_journal_entries_pet_occurred_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_occurred_at", table_name="journal_entries")
    op.drop_index("ix_journal_entries_pet_id", table_name="journal_entries")
    op.drop_table("journal_entries")
