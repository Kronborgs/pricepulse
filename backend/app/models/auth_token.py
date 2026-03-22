from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuthToken(Base):
    """
    Persisterede refresh tokens og password-reset tokens.
    Access tokens (JWT 15 min) gemmes ikke i DB — kun cookies.

    token_type:
      refresh        → langlivet refresh token (30 dage)
      password_reset → éngangsbrug ved forgot password
      email_verify   → éngangsbrug ved email-verificering
    """

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )  # SHA256 hex af raw token
    token_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # 'refresh' | 'password_reset' | 'email_verify'
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    user: Mapped["User"] = relationship(back_populates="tokens")
