from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.watch_source import WatchSource


class SourceCheck(Base):
    """
    Append-only tidsseriedata — én rad pr. check.
    Bruges til grafer, diagnostik og fejlanalyse.
    Rækker slettes aldrig — kun ved cascade fra WatchSource.
    """

    __tablename__ = "source_checks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Scrapet data
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="DKK", nullable=False)
    stock_status: Mapped[str | None] = mapped_column(String(100))

    # Fetch-metadata
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    html_length: Mapped[int | None] = mapped_column(Integer)

    # Fejlklassifikation
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Extractor info
    extractor_used: Mapped[str | None] = mapped_column(String(100))
    extractor_attempts: Mapped[list | None] = mapped_column(JSONB)   # [{name, success, reason}]

    # Flags
    bot_suspected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_price_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_stock_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rå diagnostik (title, final_url, etc.)
    raw_diagnostic: Mapped[dict | None] = mapped_column(JSONB)

    # Relations
    source: Mapped["WatchSource"] = relationship(back_populates="checks")
