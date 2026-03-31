from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.watch import Watch


class ScraperReport(Base):
    """
    Bruger-indsendt fejlrapport for en Data Webscraper (watch).
    Admin/superuser ser disse på dashboard og kan lave ny parser.
    """

    __tablename__ = "scraper_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: new → read → resolved
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relations
    watch: Mapped["Watch"] = relationship("Watch", lazy="joined")
    reporter: Mapped["User"] = relationship("User", lazy="joined")
