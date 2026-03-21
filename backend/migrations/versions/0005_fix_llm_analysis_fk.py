"""fix llm_analysis_results.watch_id FK: product_watches → watches

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-21 00:00:00.000000

Problemet:
  llm_analysis_results.watch_id har en FK til product_watches.id (v2-tabel),
  men hele det aktive system bruger den gamle v1-tabel 'watches'.
  Det medfører IntegrityError ved hver Ollama-gem → rollback → watch-objektet
  expires i SQLAlchemy-sessionen → MissingGreenlet ved næste attribut-adgang
  → prisen gemmes aldrig → watch forbliver 'Afventer'.

Løsning:
  Drop FK til product_watches, gen-anskaf FK til watches.id (ON DELETE SET NULL).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop den forkerte FK der pegede på product_watches
    op.drop_constraint(
        "llm_analysis_results_watch_id_fkey",
        "llm_analysis_results",
        type_="foreignkey",
    )
    # Opret ny FK der peger på watches (v1-tabellen der faktisk bruges)
    op.create_foreign_key(
        "llm_analysis_results_watch_id_fkey",
        "llm_analysis_results",
        "watches",
        ["watch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "llm_analysis_results_watch_id_fkey",
        "llm_analysis_results",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "llm_analysis_results_watch_id_fkey",
        "llm_analysis_results",
        "product_watches",
        ["watch_id"],
        ["id"],
        ondelete="SET NULL",
    )
