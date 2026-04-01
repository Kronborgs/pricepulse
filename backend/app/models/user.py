from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.auth_token import AuthToken
    from app.models.product_watch import ProductWatch
    from app.models.email_preference import EmailPreference
    from app.models.notification_rule import NotificationRule


class User(Base, TimestampMixin):
    """
    Systembruger med rolle-baseret adgangskontrol.

    Roller:
      admin     → fuld adgang inkl. brugerstyring og admin-sider
      superuser → kan oprette/redigere/slette watches
      (guest er ikke en konto — bare uautoriseret adgang til read-only sider)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(
        String(50), default="superuser", nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Inaktivitetstimeout i minutter. None = ingen auto-logout. 0 = brug default.
    session_timeout_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relations
    tokens: Mapped[list["AuthToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    watches: Mapped[list["ProductWatch"]] = relationship(
        back_populates="owner",
        foreign_keys="ProductWatch.owner_id",
        lazy="select",
    )
    email_preference: Mapped["EmailPreference | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    notification_rules: Mapped[list["NotificationRule"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
