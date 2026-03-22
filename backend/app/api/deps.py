"""
FastAPI dependencies til autentificering og autorisation.

Brug:
  @router.get("/admin/users")
  async def list_users(admin: User = Depends(require_role("admin"))):
      ...

  @router.get("/watches")
  async def list_watches(user: User = Depends(get_current_user)):
      ...

  # Gæst-tilladte endpoints (ingen fejl hvis ikke logget ind):
  @router.get("/dashboard")
  async def dashboard(user: User | None = Depends(get_optional_user)):
      ...
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token

logger = structlog.get_logger(__name__)


async def get_optional_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Returnerer User hvis gyldig access_token cookie, ellers None.
    Bruges på endpoints der er tilgængelige for gæster.
    """
    if not access_token:
        return None
    try:
        payload = decode_access_token(access_token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Kræver gyldig access_token cookie. Kaster 401 hvis ikke logget ind.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ikke autoriseret — log ind",
    )
    if not access_token:
        raise credentials_exception
    try:
        payload = decode_access_token(access_token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: str):
    """
    Dependency factory der kræver én af de angivne roller.

    Eksempel:
      admin_only = require_role("admin")
      superuser_or_admin = require_role("admin", "superuser")
    """
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ikke tilstrækkelige rettigheder",
            )
        return user
    return dependency


# ── Typed aliases ─────────────────────────────────────────────────────────────
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_role("admin"))]
SuperOrAdmin = Annotated[User, Depends(require_role("admin", "superuser"))]
