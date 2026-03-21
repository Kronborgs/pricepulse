from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product_watch import ProductWatch


class WatchTimelineEvent(Base):
    """
    Audit-log for alle watch og source events. Append-only — slettes aldrig.

    event_type eksempler:
      watch_created | watch_paused | watch_resumed | watch_archived
      source_added | source_url_changed | source_paused | source_resumed | source_archived
      first_price_found | price_alert | error_streak | bot_suspected
      llm_normalized | llm_parser_advice
      migrated_from_v1
    """

    __tablename__ = "watch_timeline_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_watches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relations
    watch: Mapped["ProductWatch"] = relationship(back_populates="timeline")
