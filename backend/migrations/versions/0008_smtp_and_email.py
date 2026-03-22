"""smtp_settings, email_preferences og email_queue tabeller

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-22 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── smtp_settings ─────────────────────────────────────────────────────────
    op.create_table(
        "smtp_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
        sa.Column("from_email", sa.Text(), nullable=False),
        sa.Column("from_name", sa.Text(), nullable=False, server_default="PricePulse"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── email_preferences ─────────────────────────────────────────────────────
    op.create_table(
        "email_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notify_price_drop", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_back_in_stock", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_new_error", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("digest_frequency", sa.String(20), nullable=False, server_default="weekly"),
        sa.Column("digest_day_of_week", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("digest_send_time", sa.Time(), nullable=True),
        sa.Column("last_digest_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_email_preferences_user_id", "email_preferences", ["user_id"])

    # ── email_queue ───────────────────────────────────────────────────────────
    op.create_table(
        "email_queue",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("email_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("to_email", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("related_watch_id", sa.UUID(), nullable=True),
        sa.Column("related_source_id", sa.UUID(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["related_watch_id"], ["product_watches.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["related_source_id"], ["watch_sources.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_queue_status", "email_queue", ["status"])
    op.create_index("ix_email_queue_user_id", "email_queue", ["user_id"])
    op.create_index("ix_email_queue_scheduled_for", "email_queue", ["scheduled_for"])


def downgrade() -> None:
    op.drop_table("email_queue")
    op.drop_table("email_preferences")
    op.drop_table("smtp_settings")
