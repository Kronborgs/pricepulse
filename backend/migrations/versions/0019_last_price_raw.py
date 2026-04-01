"""add last_price_raw to watch_sources

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watch_sources",
        sa.Column("last_price_raw", sa.Numeric(10, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watch_sources", "last_price_raw")
