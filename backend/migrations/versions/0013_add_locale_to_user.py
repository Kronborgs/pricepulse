"""add locale to user

Revision ID: 0013
Revises: 0012
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "locale",
            sa.String(10),
            nullable=False,
            server_default="en",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "locale")
