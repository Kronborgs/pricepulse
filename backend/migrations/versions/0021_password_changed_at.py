"""0021_password_changed_at

Tilføjer password_changed_at til users-tabellen.
Bruges til 6-måneders password-udløbspolitik.

Eksisterende brugere får sat tidspunktet til NOW() (migreringsdato),
så de ikke tvinges til at skifte med det samme.

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Sæt eksisterende brugere til nu, så de ikke tvinges til skift med det samme
    op.execute("UPDATE users SET password_changed_at = NOW() WHERE password_changed_at IS NULL")


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
