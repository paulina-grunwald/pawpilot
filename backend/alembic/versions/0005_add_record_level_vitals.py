"""Add record-level vitals columns to tractive_day_rollup.

Revision ID: 0005_add_record_level_vitals
Revises: 0004_create_journal_entries
Create Date: 2026-07-17

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_add_record_level_vitals"
down_revision: str | None = "0004_create_journal_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "tractive_day_rollup"

_COUNT_COLUMNS = (
    "heart_rate_record_count",
    "respiratory_rate_record_count",
    "respiratory_rate_night_record_count",
    "respiratory_rate_day_record_count",
)

_FLOAT_COLUMNS = (
    "heart_rate_record_mean",
    "heart_rate_ci95_half_width",
    "respiratory_rate_record_mean",
    "respiratory_rate_ci95_half_width",
    "respiratory_rate_night_record_mean",
    "respiratory_rate_day_record_mean",
)


def upgrade() -> None:
    for column_name in _COUNT_COLUMNS:
        op.add_column(
            _TABLE,
            sa.Column(
                column_name,
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
    for column_name in _FLOAT_COLUMNS:
        op.add_column(_TABLE, sa.Column(column_name, sa.Float(), nullable=True))


def downgrade() -> None:
    for column_name in reversed(_FLOAT_COLUMNS):
        op.drop_column(_TABLE, column_name)
    for column_name in reversed(_COUNT_COLUMNS):
        op.drop_column(_TABLE, column_name)
