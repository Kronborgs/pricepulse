from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationRule(Base, TimestampMixin):
    """
    Én notifikationsregel per bruger med uafhængig produktfilter og interval.
    En bruger kan have mange regler med forskelligt indhold og frekvens.

    rule_type: 'instant' | 'digest'
    filter_mode: 'all' | 'tags' | 'products'
    digest_frequency: 'hourly' | 'daily' | 'weekly' | 'monthly' (kun relevant for digest)
    """

    __tablename__ = "notification_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Visningsnavn (valgfrit)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aktiveret
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Type: øjeblikkelig eller digest
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Hændelsestyper der udløser denne regel (relevant for instant, digest bruger alle)
    notify_price_drop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_back_in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_new_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Produktfilter
    filter_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="all"
    )
    filter_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)), nullable=True
    )
    filter_product_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )

    # Digest-indstillinger
    digest_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    digest_day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    digest_send_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    last_digest_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    user: Mapped["User"] = relationship(back_populates="notification_rules")
