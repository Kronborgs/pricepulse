"""Tilføj tags til products

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-01 00:00:00.000000

Ændringer:
  1. products.tags — ARRAY(VARCHAR(100)), nullable, GIN-indeks for hurtig søgning
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
    op.add_column(
        "products",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_products_tags",
        "products",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_products_tags", table_name="products")
    op.drop_column("products", "tags")
