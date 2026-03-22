from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EmailQueue(Base):
    """
    Kø til udgående emails. APScheduler-job sender pending mails hvert 5. min.

    email_type:
      welcome          → velkomstmail ved oprettelse
      password_reset   → reset-link
      email_verify     → verifikationslink
      price_drop       → pris faldet under threshold
      back_in_stock    → produkt tilbage på lager
      digest           → periodisk oversigt
      test             → test-mail fra SMTP-indstillinger

    status: 'pending' | 'sent' | 'failed'
    Max 3 forsøg (attempts). Ved failure markeres status='failed'.
    """

    __tablename__ = "email_queue"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )
    to_email: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)

    # Kontekst-relationer (nullable)
    related_watch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_watches.id", ondelete="SET NULL"), nullable=True
    )
    related_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="SET NULL"), nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="select")
