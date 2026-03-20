"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── shops ──────────────────────────────────────────────────────────────────
    op.create_table(
        "shops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(200), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("default_provider", sa.String(50), nullable=False, server_default="http"),
        sa.Column("default_price_selector", sa.Text(), nullable=True),
        sa.Column("default_title_selector", sa.Text(), nullable=True),
        sa.Column("default_stock_selector", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_index("ix_shops_domain", "shops", ["domain"])

    # ── products ───────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("ean", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_ean", "products", ["ean"])

    # ── watches ────────────────────────────────────────────────────────────────
    op.create_table(
        "watches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("current_currency", sa.String(3), nullable=False, server_default="DKK"),
        sa.Column("current_stock_status", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("check_interval", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("provider", sa.String(50), nullable=False, server_default="http"),
        sa.Column("scraper_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watches_shop_id", "watches", ["shop_id"])
    op.create_index("ix_watches_product_id", "watches", ["product_id"])
    op.create_index("ix_watches_status", "watches", ["status"])

    # ── price_history ──────────────────────────────────────────────────────────
    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("watch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="DKK"),
        sa.Column("stock_status", sa.String(100), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_change", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["watch_id"], ["watches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_history_watch_id", "price_history", ["watch_id"])
    op.create_index("ix_price_history_recorded_at", "price_history", ["recorded_at"])

    # ── price_events ───────────────────────────────────────────────────────────
    op.create_table(
        "price_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("watch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("old_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_delta", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_delta_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("old_stock", sa.String(100), nullable=True),
        sa.Column("new_stock", sa.String(100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dedup_key", sa.String(300), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["watch_id"], ["watches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key"),
    )
    op.create_index("ix_price_events_watch_id", "price_events", ["watch_id"])
    op.create_index("ix_price_events_event_type", "price_events", ["event_type"])
    op.create_index("ix_price_events_occurred_at", "price_events", ["occurred_at"])
    op.create_index("ix_price_events_dedup_key", "price_events", ["dedup_key"])


def downgrade() -> None:
    op.drop_table("price_events")
    op.drop_table("price_history")
    op.drop_table("watches")
    op.drop_table("products")
    op.drop_table("shops")
