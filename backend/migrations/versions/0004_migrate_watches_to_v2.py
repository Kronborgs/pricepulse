"""v2 data migration: watches → product_watches + watch_sources

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-21 00:00:00.000000

Migrerer eksisterende v1-data til v2-modellen:
  watches         → product_watches + watch_sources
  price_history   → source_checks
  price_events    → source_price_events

De originale v1-tabeller bevares uændret (læse-only backup).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Trin 1: Opret manglende Products for watches uden product_id ──────────
    # Watches uden product_id får et nyt product oprettet fra title/url
    conn.execute(sa.text("""
        INSERT INTO products (id, name, status, is_active, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            COALESCE(NULLIF(TRIM(w.title), ''), 'Ukendt produkt (' || w.url || ')'),
            'active',
            true,
            w.created_at,
            w.updated_at
        FROM watches w
        WHERE w.product_id IS NULL
    """))

    # Opdatér watches.product_id til de nyoprettede products
    # Vi matcher på created_at + url for at finde de rigtige pairs
    conn.execute(sa.text("""
        UPDATE watches w
        SET product_id = p.id
        FROM products p
        WHERE w.product_id IS NULL
          AND p.name = COALESCE(NULLIF(TRIM(w.title), ''), 'Ukendt produkt (' || w.url || ')')
          AND p.created_at = w.created_at
    """))

    # ── Trin 2: Opret product_watches fra watches ─────────────────────────────
    conn.execute(sa.text("""
        INSERT INTO product_watches (
            id, product_id, name, default_interval_min, status,
            last_best_price, last_checked_at,
            paused_at, archived_at, created_at, updated_at
        )
        SELECT
            w.id,                               -- genbruger samme UUID som watch
            w.product_id,
            w.title,
            w.check_interval,
            CASE
                WHEN NOT w.is_active          THEN 'archived'
                WHEN w.status = 'blocked'     THEN 'error'
                ELSE w.status
            END,
            w.current_price,
            w.last_checked_at,
            NULL,                               -- paused_at
            CASE WHEN NOT w.is_active THEN w.updated_at ELSE NULL END,
            w.created_at,
            w.updated_at
        FROM watches w
        WHERE w.product_id IS NOT NULL
    """))

    # ── Trin 3: Opret watch_sources fra watches ───────────────────────────────
    conn.execute(sa.text("""
        INSERT INTO watch_sources (
            id, watch_id, shop, url,
            status, provider, scraper_config,
            last_check_at, next_check_at,
            last_price, last_currency, last_stock_status,
            last_error_type, last_error_message, last_diagnostic,
            consecutive_errors,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            w.id,                               -- watch_id = product_watch.id (samme UUID)
            COALESCE(s.domain, 'ukendt'),
            w.url,
            CASE
                WHEN NOT w.is_active          THEN 'archived'
                WHEN w.status = 'blocked'     THEN 'blocked'
                ELSE w.status
            END,
            w.provider,
            w.scraper_config,
            w.last_checked_at,
            NULL,                               -- next_check_at — sættes af scheduler
            w.current_price,
            w.current_currency,
            w.current_stock_status,
            (w.last_diagnostic->>'error_type'),
            w.last_error,
            w.last_diagnostic,
            w.error_count,
            w.created_at,
            w.updated_at
        FROM watches w
        LEFT JOIN shops s ON s.id = w.shop_id
        WHERE w.product_id IS NOT NULL
    """))

    # Gem mapping watches.id → watch_sources.id i en temp-tabel
    # (vi skal bruge det til source_checks og source_price_events)
    conn.execute(sa.text("""
        CREATE TEMP TABLE _v2_source_map AS
        SELECT
            ws.watch_id AS watch_id,        -- = watches.id
            ws.id       AS source_id
        FROM watch_sources ws
        WHERE ws.watch_id IN (SELECT id FROM product_watches)
    """))

    # ── Trin 4: Migrer price_history → source_checks ─────────────────────────
    conn.execute(sa.text("""
        INSERT INTO source_checks (
            source_id, checked_at,
            price, currency, stock_status,
            success,
            is_price_change, is_stock_change,
            raw_diagnostic
        )
        SELECT
            m.source_id,
            ph.recorded_at,
            ph.price,
            ph.currency,
            ph.stock_status,
            true,               -- historiske checks var succesfulde
            ph.is_change,
            false,              -- stock-change info ikke gemt i v1
            ph.raw_data
        FROM price_history ph
        JOIN _v2_source_map m ON m.watch_id = ph.watch_id
    """))

    # ── Trin 5: Migrer price_events → source_price_events ────────────────────
    conn.execute(sa.text("""
        INSERT INTO source_price_events (
            source_id, old_price, new_price,
            old_stock, new_stock,
            change_type, created_at
        )
        SELECT
            m.source_id,
            pe.old_price,
            pe.new_price,
            pe.old_stock,
            pe.new_stock,
            CASE pe.event_type
                WHEN 'initial'      THEN 'initial'
                WHEN 'price_change' THEN CASE
                    WHEN pe.price_delta > 0 THEN 'increase'
                    ELSE 'decrease'
                END
                WHEN 'stock_change' THEN CASE
                    WHEN pe.new_stock ILIKE '%på lager%'
                      OR pe.new_stock ILIKE '%in stock%' THEN 'back_in_stock'
                    ELSE 'unavailable'
                END
                ELSE 'initial'
            END,
            pe.occurred_at
        FROM price_events pe
        JOIN _v2_source_map m ON m.watch_id = pe.watch_id
    """))

    # ── Trin 6: Opret migrerings-events i timeline ───────────────────────────
    conn.execute(sa.text("""
        INSERT INTO watch_timeline_events (watch_id, source_id, event_type, event_data, created_at)
        SELECT
            pw.id,
            ws.id,
            'migrated_from_v1',
            jsonb_build_object(
                'v1_watch_id', pw.id::text,
                'url', ws.url,
                'migrated_at', NOW()
            ),
            NOW()
        FROM product_watches pw
        JOIN watch_sources ws ON ws.watch_id = pw.id
    """))

    # ── Trin 7: Aktiver sources — sæt next_check_at ───────────────────────────
    conn.execute(sa.text("""
        UPDATE watch_sources
        SET
            status = 'active',
            next_check_at = NOW()
        WHERE status = 'pending'
    """))

    conn.execute(sa.text("DROP TABLE _v2_source_map"))


def downgrade() -> None:
    # Data-migrations kan ikke rulles meningsfuldt tilbage automatisk.
    # Tabellerne tømmes så 0003-downgrade kan køre.
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM watch_timeline_events WHERE event_type = 'migrated_from_v1'"))
    conn.execute(sa.text("DELETE FROM source_price_events"))
    conn.execute(sa.text("DELETE FROM source_checks"))
    conn.execute(sa.text("DELETE FROM watch_sources"))
    conn.execute(sa.text("DELETE FROM product_watches"))
    # Fjern kolonne-tilføjelser til products igen
    conn.execute(sa.text("UPDATE products SET status = 'active'"))
