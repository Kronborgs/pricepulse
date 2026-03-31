"""Tilføj owner_id til watches og products

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-31 00:00:00.000000

Ændringer:
  1. watches.owner_id  — FK til users.id (SET NULL), nullable
  2. products.owner_id — FK til users.id (SET NULL), nullable

Eksisterende rækker får owner_id = NULL (de tilhører "systemet").
product_watches.owner_id eksisterer allerede (fra 0009).

Rolle-systemet (admin / superuser / user) kræver ingen DB-migration
da 'role' er en VARCHAR(50) kolonne uden constraint.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── watches.owner_id ──────────────────────────────────────────────────────
    op.add_column(
        "watches",
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_watches_owner_id", "watches", ["owner_id"])

    # ── products.owner_id ─────────────────────────────────────────────────────
    op.add_column(
        "products",
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_products_owner_id", "products", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_products_owner_id", table_name="products")
    op.drop_column("products", "owner_id")

    op.drop_index("ix_watches_owner_id", table_name="watches")
    op.drop_column("watches", "owner_id")
