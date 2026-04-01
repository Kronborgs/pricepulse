from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class EmailPreference(Base, TimestampMixin):
    """
    Per-bruger indstillinger for email-notifikationer og digest.

    digest_frequency: 'daily' | 'weekly' | 'monthly'
    digest_day_of_week: 0-6 (mandag=0, kun brugt ved weekly)
    """

    __tablename__ = "email_preferences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Hændelsesnotifikationer
    notify_price_drop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_back_in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_new_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_on_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Digest
    # digest_frequency: 'hourly' | 'daily' | 'weekly' | 'monthly'
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    digest_frequency: Mapped[str] = mapped_column(
        String(20), default="weekly", nullable=False
    )
    digest_day_of_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    digest_send_time: Mapped[time | None] = mapped_column(Time)
    last_digest_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Notifikationsfilter
    # notify_filter_mode: 'all' | 'tags' | 'products'
    notify_filter_mode: Mapped[str] = mapped_column(
        String(20), default="all", nullable=False, server_default="all"
    )
    notify_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)), nullable=True
    )
    notify_product_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )

    # Relations
    user: Mapped["User"] = relationship(back_populates="email_preference")
