"""
AuthService — JWT-baseret autentificering med httpOnly cookies.

Access token:  JWT, 15 min, sættes som httpOnly cookie 'access_token'
Refresh token: random bytes, 30 dage, SHA256-hash gemmes i auth_tokens,
               sættes som httpOnly cookie 'refresh_token'

First-run:
  Hvis ingen brugere eksisterer returnerer setup_required=True fra /api/auth/setup-status.
  Frontend redirecter til /setup for oprettelse af første admin.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth_token import AuthToken
from app.models.user import User

logger = structlog.get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _hash_token(raw: str) -> str:
    """SHA256-hash af raw token → gemmes i DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Dekoder og validerer JWT. Kaster JWTError ved ugyldig/udløbet token."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


# ── AuthService ───────────────────────────────────────────────────────────────

class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── First-run ─────────────────────────────────────────────────────────────

    async def setup_required(self) -> bool:
        """True hvis ingen brugere eksisterer — systemet er ikke sat op."""
        count = await self.db.scalar(select(func.count(User.id)))
        return count == 0

    async def create_first_admin(
        self, email: str, password: str, display_name: str | None = None
    ) -> User:
        """Opretter første admin-bruger. Kaster ValueError hvis bruger allerede eksisterer."""
        if not await self.setup_required():
            raise ValueError("Systemet er allerede sat op — brug bruger-admin")
        return await self._create_user(email, password, role="admin", display_name=display_name)

    # ── Users ─────────────────────────────────────────────────────────────────

    async def create_user(
        self,
        email: str,
        password: str,
        role: str = "superuser",
        display_name: str | None = None,
    ) -> User:
        """Opretter bruger. Kaster ValueError hvis email allerede er i brug."""
        existing = await self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise ValueError("Email er allerede i brug")
        return await self._create_user(email, password, role=role, display_name=display_name)

    async def _create_user(
        self, email: str, password: str, role: str, display_name: str | None
    ) -> User:
        user = User(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role=role,
            display_name=display_name or email.split("@")[0],
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("user_created", user_id=str(user.id), role=role)
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        """Returner User hvis credentials er korrekte, ellers None."""
        user = await self.db.scalar(
            select(User).where(User.email == email.lower().strip())
        )
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        # Opdatér last_login_at
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    # ── Tokens ────────────────────────────────────────────────────────────────

    async def create_refresh_token(self, user_id: uuid.UUID) -> str:
        """Opretter nyt refresh token, gemmer hash i DB, returnerer raw token."""
        raw = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        token = AuthToken(
            user_id=user_id,
            token_hash=_hash_token(raw),
            token_type="refresh",
            expires_at=expires,
        )
        self.db.add(token)
        await self.db.commit()
        return raw

    async def rotate_refresh_token(self, raw_refresh: str) -> tuple[User, str] | None:
        """
        Valider refresh token, revoke det og udsted nyt.
        Returner (user, new_raw_refresh) eller None ved ugyldig token.
        """
        hashed = _hash_token(raw_refresh)
        now = datetime.now(timezone.utc)
        token_row = await self.db.scalar(
            select(AuthToken).where(
                AuthToken.token_hash == hashed,
                AuthToken.token_type == "refresh",
                AuthToken.revoked_at.is_(None),
                AuthToken.expires_at > now,
            )
        )
        if not token_row:
            return None

        # Revoke gammelt token
        token_row.revoked_at = now
        await self.db.flush()

        user = await self.db.get(User, token_row.user_id)
        if not user or not user.is_active:
            await self.db.rollback()
            return None

        new_raw = await self.create_refresh_token(user.id)
        return user, new_raw

    async def revoke_all_refresh_tokens(self, user_id: uuid.UUID) -> None:
        """Logout alle sessioner for bruger."""
        from sqlalchemy import update
        await self.db.execute(
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.token_type == "refresh",
                AuthToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def create_password_reset_token(self, email: str) -> str | None:
        """
        Opretter password-reset token.
        Returnerer raw token (sendes via mail) eller None hvis email ikke findes.
        """
        user = await self.db.scalar(
            select(User).where(User.email == email.lower().strip(), User.is_active == True)
        )
        if not user:
            return None

        raw = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=2)
        self.db.add(AuthToken(
            user_id=user.id,
            token_hash=_hash_token(raw),
            token_type="password_reset",
            expires_at=expires,
        ))
        await self.db.commit()
        return raw

    async def reset_password(self, raw_token: str, new_password: str) -> bool:
        """
        Validerer reset-token og sætter nyt password.
        Returnerer True ved succes, False ved ugyldigt/udløbet token.
        """
        hashed = _hash_token(raw_token)
        now = datetime.now(timezone.utc)
        token_row = await self.db.scalar(
            select(AuthToken).where(
                AuthToken.token_hash == hashed,
                AuthToken.token_type == "password_reset",
                AuthToken.revoked_at.is_(None),
                AuthToken.expires_at > now,
            )
        )
        if not token_row:
            return False

        user = await self.db.get(User, token_row.user_id)
        if not user:
            return False

        user.password_hash = hash_password(new_password)
        token_row.revoked_at = now
        await self.db.commit()

        # Revoke alle refresh tokens (tving re-login)
        await self.revoke_all_refresh_tokens(user.id)
        logger.info("password_reset", user_id=str(user.id))
        return True

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def cleanup_expired_tokens(self) -> int:
        """Slet udløbne tokens. Køres af APScheduler dagligt."""
        from sqlalchemy import delete
        result = await self.db.execute(
            delete(AuthToken).where(
                AuthToken.expires_at < datetime.now(timezone.utc)
            )
        )
        await self.db.commit()
        count = result.rowcount
        if count > 0:
            logger.info("auth_tokens_cleaned", count=count)
        return count


auth_service_factory = AuthService
