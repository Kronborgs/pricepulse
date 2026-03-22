"""Fix ai_jobs.watch_id FK — fjern FK til product_watches

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-22 00:00:00.000000

Problemet: watch_id i ai_jobs har en FK-constraint til product_watches,
men v1-watches (watches-tabellen) bruger samme kolonne → FK-violation
ved hvert INSERT, og der gemmes aldrig noget i ai_jobs.

Løsning: Fjern FK-constrainten så watch_id er en "soft reference"
UUID-kolonne uden DB-enforcement. Begge v1 (watches) og v2
(product_watches) IDs kan nu gemmes uden fejl.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ai_jobs_watch_id_fkey", "ai_jobs", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key(
        "ai_jobs_watch_id_fkey",
        "ai_jobs",
        "product_watches",
        ["watch_id"],
        ["id"],
        ondelete="SET NULL",
    )
