"""add currency_hint to watch_sources

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE watch_sources
        ADD COLUMN IF NOT EXISTS currency_hint VARCHAR(3) DEFAULT NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE watch_sources DROP COLUMN IF EXISTS currency_hint")
