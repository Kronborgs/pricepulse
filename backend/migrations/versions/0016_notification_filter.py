"""Tilføj notifikationsfilter til email_preferences

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-01 00:00:00.000000

Ændringer:
  1. email_preferences.notify_filter_mode — VARCHAR(20), default 'all'
  2. email_preferences.notify_tags        — ARRAY(VARCHAR(100)), nullable
  3. email_preferences.notify_product_ids — ARRAY(UUID), nullable
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_preferences",
        sa.Column(
            "notify_filter_mode",
            sa.String(20),
            nullable=False,
            server_default="all",
        ),
    )
    op.add_column(
        "email_preferences",
        sa.Column(
            "notify_tags",
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
        ),
    )
    op.add_column(
        "email_preferences",
        sa.Column(
            "notify_product_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("email_preferences", "notify_product_ids")
    op.drop_column("email_preferences", "notify_tags")
    op.drop_column("email_preferences", "notify_filter_mode")
