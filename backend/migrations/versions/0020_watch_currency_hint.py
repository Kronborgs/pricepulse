"""Add currency_hint and current_price_raw to watches

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watches", sa.Column("currency_hint", sa.String(3), nullable=True))
    op.add_column("watches", sa.Column("current_price_raw", sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("watches", "current_price_raw")
    op.drop_column("watches", "currency_hint")
