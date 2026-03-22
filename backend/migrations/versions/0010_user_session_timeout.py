"""0010_user_session_timeout

Tilføjer session_timeout_minutes til users-tabellen.
Null = ingen auto-logout fra inaktivitet.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: str = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_timeout_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "session_timeout_minutes")
