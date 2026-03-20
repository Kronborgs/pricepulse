from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.watch import Watch


class PriceHistory(Base):
    """
    Tidsseriedata — én rad pr. check.
    Alle checks gemmes her (inkl. uændrede) for at tegne fulde grafer.
    is_change=True markerer at prisen/lageret ændrede sig ved dette check.
    """

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True
    )

    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="DKK", nullable=False)
    stock_status: Mapped[str | None] = mapped_column(String(100))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    is_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rå JSON-data fra scraper (til debugging)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relations
    watch: Mapped["Watch"] = relationship(back_populates="price_history")
