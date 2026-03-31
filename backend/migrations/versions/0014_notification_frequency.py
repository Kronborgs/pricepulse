"""Tilføj notify_on_change og hourly digest-frekvens til email_preferences

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-31 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_preferences",
        sa.Column(
            "notify_on_change",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("email_preferences", "notify_on_change")
