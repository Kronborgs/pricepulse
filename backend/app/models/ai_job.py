from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.watch_source import WatchSource
    from app.models.product_watch import ProductWatch
    from app.models.product import Product
    from app.models.user import User


class AIJob(Base):
    """
    Audit log for alle Ollama-kald.

    job_type:
      parser_advice       → forslag til selectors ved parse-fejl
      normalization       → produktnormalisering (brand, model, MPN)
      product_matching    → sammenligner to sources (same product?)
      selector_suggest    → foreslår CSS-selectors til ny URL

    status:
      queued      → venter i kø
      processing  → sendt til Ollama
      completed   → svar modtaget
      failed      → fejl
      cancelled   → annulleret

    Rækker slettes aldrig — permanent audit trail.
    """

    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False, index=True
    )
    model_used: Mapped[str | None] = mapped_column(String(200))

    # Relationer til kontekst (nullable — ikke alle jobs har alle)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    watch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_watches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Data — gem aldrig fuld HTML; brug slim_html_for_prompt før lagring
    prompt_summary: Mapped[str | None] = mapped_column(Text)
    input_data: Mapped[dict | None] = mapped_column(JSONB)   # prompt context (beskåret)
    output_data: Mapped[dict | None] = mapped_column(JSONB)  # råt Ollama-svar
    summary: Mapped[str | None] = mapped_column(Text)        # genereret resumé til UI

    error_message: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    response_tokens: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations (ingen cascade — vi sletter aldrig ai_jobs)
    source: Mapped["WatchSource | None"] = relationship(
        foreign_keys=[source_id], lazy="select"
    )
    watch: Mapped["ProductWatch | None"] = relationship(
        foreign_keys=[watch_id], lazy="select"
    )
    triggered_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[triggered_by], lazy="select"
    )
