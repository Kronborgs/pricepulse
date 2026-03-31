"""Tilføj scraper_reports tabel

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-31 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraper_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "watch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_scraper_reports_watch_id", "scraper_reports", ["watch_id"])
    op.create_index("ix_scraper_reports_reporter_id", "scraper_reports", ["reporter_id"])
    op.create_index("ix_scraper_reports_status", "scraper_reports", ["status"])
    op.create_index("ix_scraper_reports_created_at", "scraper_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_scraper_reports_created_at", table_name="scraper_reports")
    op.drop_index("ix_scraper_reports_status", table_name="scraper_reports")
    op.drop_index("ix_scraper_reports_reporter_id", table_name="scraper_reports")
    op.drop_index("ix_scraper_reports_watch_id", table_name="scraper_reports")
    op.drop_table("scraper_reports")
