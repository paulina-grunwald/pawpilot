"""Add sleep architecture columns to tractive_day_rollup.

Revision ID: 0007_add_sleep_architecture
Revises: 0006_add_outings
Create Date: 2026-07-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_add_sleep_architecture"
down_revision: str | None = "0006_add_outings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "tractive_day_rollup"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "sleep_longest_bout_minutes",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column("sleep_bout_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(_TABLE, sa.Column("sleep_fragmentation_index", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column(_TABLE, "sleep_fragmentation_index")
    op.drop_column(_TABLE, "sleep_bout_count")
    op.drop_column(_TABLE, "sleep_longest_bout_minutes")
