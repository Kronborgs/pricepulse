"""ai_jobs tabel — audit log for alle Ollama-kald

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-22 00:00:00.000000

Migrerer eksisterende llm_analysis_results til ai_jobs som historik.
llm_analysis_results bevares som cache-tabel.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("model_used", sa.String(200), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("watch_id", sa.UUID(), nullable=True),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("triggered_by", sa.UUID(), nullable=True),
        sa.Column("prompt_summary", sa.Text(), nullable=True),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("response_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["watch_sources.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["watch_id"], ["product_watches.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_jobs_job_type", "ai_jobs", ["job_type"])
    op.create_index("ix_ai_jobs_status", "ai_jobs", ["status"])
    op.create_index("ix_ai_jobs_source_id", "ai_jobs", ["source_id"])
    op.create_index("ix_ai_jobs_watch_id", "ai_jobs", ["watch_id"])
    op.create_index("ix_ai_jobs_queued_at", "ai_jobs", ["queued_at"])

    # Migrer eksisterende llm_analysis_results som completed ai_jobs
    op.execute("""
        INSERT INTO ai_jobs (
            id, job_type, status, model_used,
            source_id, input_data, output_data,
            prompt_tokens, response_tokens,
            queued_at, completed_at, created_at
        )
        SELECT
            gen_random_uuid(),
            analysis_type,
            'completed',
            model_used,
            source_id,
            input_data,
            output_data,
            prompt_tokens,
            response_tokens,
            created_at,
            created_at,
            created_at
        FROM llm_analysis_results
    """)


def downgrade() -> None:
    op.drop_table("ai_jobs")
