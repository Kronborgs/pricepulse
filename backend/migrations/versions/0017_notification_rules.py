"""Opret notification_rules tabel

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-01 00:00:00.000000

Ændringer:
  1. notification_rules — ny tabel til per-bruger notifikationsregler
     med uafhængige produktfiltre og intervaller
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("notify_price_drop", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_back_in_stock", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_change", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notify_new_error", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("filter_mode", sa.String(20), nullable=False, server_default="all"),
        sa.Column(
            "filter_tags",
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
        ),
        sa.Column(
            "filter_product_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("digest_frequency", sa.String(20), nullable=True),
        sa.Column("digest_day_of_week", sa.Integer(), nullable=True),
        sa.Column("digest_send_time", sa.Time(), nullable=True),
        sa.Column("last_digest_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_notification_rules_user_id",
        "notification_rules",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_rules_user_id", table_name="notification_rules")
    op.drop_table("notification_rules")
