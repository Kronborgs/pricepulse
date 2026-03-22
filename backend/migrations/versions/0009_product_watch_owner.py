"""product_watches: owner_id + notifikationsfelter

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-22 00:00:00.000000

Tilføjer owner_id (FK → users), notify_on_price_drop, notify_on_back_in_stock
og price_threshold til product_watches.
Eksisterende watches får owner_id = NULL (systemoprettede).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_watches",
        sa.Column("owner_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_product_watches_owner",
        "product_watches",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_product_watches_owner_id", "product_watches", ["owner_id"])

    op.add_column(
        "product_watches",
        sa.Column(
            "notify_on_price_drop",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "product_watches",
        sa.Column(
            "notify_on_back_in_stock",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
    op.add_column(
        "product_watches",
        sa.Column("price_threshold", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_watches", "price_threshold")
    op.drop_column("product_watches", "notify_on_back_in_stock")
    op.drop_column("product_watches", "notify_on_price_drop")
    op.drop_constraint("fk_product_watches_owner", "product_watches", type_="foreignkey")
    op.drop_index("ix_product_watches_owner_id", "product_watches")
    op.drop_column("product_watches", "owner_id")
