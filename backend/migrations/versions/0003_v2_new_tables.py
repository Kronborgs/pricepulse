"""v2 schema: product_watches, watch_sources, source_checks + Ollama tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-21 00:00:00.000000

Opretter alle v2-tabeller. De eksisterende v1-tabeller (watches, price_history,
price_events) berøres ikke — migration 0004 migrerer data.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tilføj nye kolonner til products ──────────────────────────────────────
    op.add_column("products", sa.Column("model", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("variant", sa.String(200), nullable=True))
    op.add_column("products", sa.Column("mpn", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("status", sa.String(50), nullable=False,
                                        server_default="active"))
    op.add_column("products", sa.Column("ollama_normalized_at",
                                        sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("normalization_confidence", sa.Float(), nullable=True))
    op.add_column("products", sa.Column("normalization_data",
                                        postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index("ix_products_mpn", "products", ["mpn"])
    op.create_index("ix_products_status", "products", ["status"])

    # ── product_watches ───────────────────────────────────────────────────────
    # last_best_source_id FK tilføjes EFTER watch_sources er oprettet
    op.create_table(
        "product_watches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("default_interval_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("last_best_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("last_best_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_watches_product_id", "product_watches", ["product_id"])
    op.create_index("ix_product_watches_status", "product_watches", ["status"])

    # ── watch_sources ─────────────────────────────────────────────────────────
    op.create_table(
        "watch_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("watch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("previous_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("interval_override_min", sa.Integer(), nullable=True),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("last_currency", sa.String(3), nullable=False, server_default="DKK"),
        sa.Column("last_stock_status", sa.String(100), nullable=True),
        sa.Column("last_error_type", sa.String(100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("last_diagnostic",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("consecutive_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bot_suspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="http"),
        sa.Column("scraper_config",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["watch_id"], ["product_watches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_watch_sources_watch_id", "watch_sources", ["watch_id"])
    op.create_index("ix_watch_sources_status", "watch_sources", ["status"])
    op.create_index("ix_watch_sources_next_check_at", "watch_sources", ["next_check_at"])

    # Nu kan vi tilføje den cirkulære FK fra product_watches → watch_sources
    op.create_foreign_key(
        "fk_product_watches_last_best_source",
        "product_watches", "watch_sources",
        ["last_best_source_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── source_checks ─────────────────────────────────────────────────────────
    op.create_table(
        "source_checks",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="DKK"),
        sa.Column("stock_status", sa.String(100), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("html_length", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extractor_used", sa.String(100), nullable=True),
        sa.Column("extractor_attempts",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bot_suspected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_price_change", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_stock_change", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_diagnostic",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["watch_sources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_source_checks_source_id_checked_at", "source_checks",
                    ["source_id", "checked_at"])
    op.create_index("ix_source_checks_checked_at", "source_checks", ["checked_at"])

    # ── source_price_events ───────────────────────────────────────────────────
    op.create_table(
        "source_price_events",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_id", sa.BigInteger(), nullable=True),
        sa.Column("old_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("old_stock", sa.String(100), nullable=True),
        sa.Column("new_stock", sa.String(100), nullable=True),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["watch_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["check_id"], ["source_checks.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_source_price_events_source_id", "source_price_events",
                    ["source_id", "created_at"])

    # ── product_snapshots ─────────────────────────────────────────────────────
    op.create_table(
        "product_snapshots",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("watch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("best_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("best_price_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("avg_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("shops_with_stock", sa.Integer(), nullable=True),
        sa.Column("active_shops", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["watch_id"], ["product_watches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["best_price_source_id"], ["watch_sources.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_product_snapshots_watch_id_snapshot_at",
                    "product_snapshots", ["watch_id", "snapshot_at"])

    # ── watch_timeline_events ─────────────────────────────────────────────────
    op.create_table(
        "watch_timeline_events",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("watch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_data",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["watch_id"], ["product_watches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["watch_sources.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_watch_timeline_events_watch_id", "watch_timeline_events",
                    ["watch_id", "created_at"])
    op.create_index("ix_watch_timeline_events_source_id", "watch_timeline_events",
                    ["source_id", "created_at"])

    # ── llm_analysis_results ──────────────────────────────────────────────────
    op.create_table(
        "llm_analysis_results",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("watch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_type", sa.String(100), nullable=False),
        sa.Column("model_used", sa.String(200), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("response_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_key", sa.String(64), nullable=True),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("input_data",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_data",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["watch_sources.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["watch_id"], ["product_watches.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_llm_analysis_results_cache_key", "llm_analysis_results", ["cache_key"])
    op.create_index("ix_llm_analysis_results_source_id", "llm_analysis_results", ["source_id"])
    op.create_index("ix_llm_analysis_results_watch_id", "llm_analysis_results", ["watch_id"])


def downgrade() -> None:
    op.drop_table("llm_analysis_results")
    op.drop_table("watch_timeline_events")
    op.drop_table("product_snapshots")
    op.drop_table("source_price_events")
    op.drop_table("source_checks")

    op.drop_constraint(
        "fk_product_watches_last_best_source", "product_watches", type_="foreignkey"
    )
    op.drop_table("watch_sources")
    op.drop_table("product_watches")

    op.drop_index("ix_products_status", "products")
    op.drop_index("ix_products_mpn", "products")
    op.drop_column("products", "normalization_data")
    op.drop_column("products", "normalization_confidence")
    op.drop_column("products", "ollama_normalized_at")
    op.drop_column("products", "status")
    op.drop_column("products", "mpn")
    op.drop_column("products", "variant")
    op.drop_column("products", "model")
