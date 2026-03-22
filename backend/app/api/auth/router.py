"""
Auth API endpoints — login, logout, setup, password reset, me.
Cookies sættes som httpOnly, Secure (i prod), SameSite=Lax.
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_optional_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService, create_access_token

logger = structlog.get_logger(__name__)
router = APIRouter()

_SECURE = settings.cookie_secure
_SAMESITE = "lax"


# ── Schemas ───────────────────────────────────────────────────────────────────

class SetupRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    is_active: bool
    email_verified: bool
    created_at: str

    model_config = {"from_attributes": True}


class SetupStatus(BaseModel):
    setup_required: bool


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "superuser"
    display_name: str | None = None


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    session_timeout_minutes: int | None = None  # 0 = deaktiveret, None = uændret


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_SECURE,
        samesite=_SAMESITE,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=_SECURE,
        samesite=_SAMESITE,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _user_to_read(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "session_timeout_minutes": getattr(user, "session_timeout_minutes", None),
        "created_at": user.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/setup-status", response_model=SetupStatus)
async def setup_status(db: AsyncSession = Depends(get_db)) -> SetupStatus:
    """Returnerer om systemet mangler første admin. Frontend checker dette ved opstart."""
    svc = AuthService(db)
    return SetupStatus(setup_required=await svc.setup_required())


@router.post("/setup", response_model=UserRead)
async def setup(
    body: SetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Opret første admin. Kun tilladt hvis ingen brugere eksisterer."""
    svc = AuthService(db)
    try:
        user = await svc.create_first_admin(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    access = create_access_token(user.id, user.role)
    refresh = await svc.create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)
    logger.info("first_admin_created", user_id=str(user.id))
    return _user_to_read(user)


@router.post("/login", response_model=UserRead)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Login med email + password. Sætter httpOnly cookies ved succes."""
    svc = AuthService(db)
    user = await svc.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forkert email eller kodeord",
        )

    access = create_access_token(user.id, user.role)
    refresh = await svc.create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)
    return _user_to_read(user)


@router.post("/logout")
async def logout(
    response: Response,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Logger ud og revoker alle refresh tokens."""
    if user:
        svc = AuthService(db)
        await svc.revoke_all_refresh_tokens(user.id)
    _clear_auth_cookies(response)
    return {"ok": True}


@router.post("/refresh")
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> dict:
    """
    Roter refresh token → ny access token + ny refresh token.
    Læser 'refresh_token' fra httpOnly cookie (path=/api/v1/auth/refresh).
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Ingen refresh token")

    svc = AuthService(db)
    result = await svc.rotate_refresh_token(refresh_token)
    if not result:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Ugyldig eller udløbet session")

    user, new_refresh = result
    access = create_access_token(user.id, user.role)
    _set_auth_cookies(response, access, new_refresh)
    return {"ok": True}


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> dict:
    """Returnerer den aktuelle brugers data."""
    return _user_to_read(user)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Sender password-reset mail hvis email findes.
    Returnerer altid 200 for at forhindre enumeration.
    """
    svc = AuthService(db)
    raw_token = await svc.create_password_reset_token(body.email)
    if raw_token:
        # Kø reset-mail — importér her for at undgå cirkulære imports
        try:
            from app.services.smtp_service import smtp_service
            await smtp_service.queue_password_reset(
                db=db, email=body.email, token=raw_token
            )
        except Exception:
            logger.warning("forgot_password_mail_fejl", email=body.email)
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Nulstiller kodeord med éngangsbrug-token fra mail."""
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Kodeord skal være mindst 8 tegn")
    svc = AuthService(db)
    ok = await svc.reset_password(body.token, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Ugyldigt eller udløbet reset-link")
    return {"ok": True}


# ── Admin: bruger-CRUD ────────────────────────────────────────────────────────

@router.get("/admin/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin")),
) -> dict:
    from sqlalchemy import select, func
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    total = await db.scalar(select(func.count(User.id)))
    return {
        "items": [_user_to_read(u) for u in users],
        "total": total or 0,
    }


@router.post("/admin/users", response_model=UserRead)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin")),
) -> dict:
    svc = AuthService(db)
    try:
        user = await svc.create_user(
            email=body.email,
            password=body.password,
            role=body.role,
            display_name=body.display_name,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Send velkomstmail
    try:
        from app.services.smtp_service import smtp_service
        await smtp_service.queue_welcome(db=db, user=user)
    except Exception:
        pass

    return _user_to_read(user)


@router.patch("/admin/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin")),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Bruger ikke fundet")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        if body.role not in ("admin", "superuser"):
            raise HTTPException(status_code=400, detail="Ugyldig rolle")
        user.role = body.role
    if body.is_active is not None:
        from datetime import datetime, timezone
        user.is_active = body.is_active
        if not body.is_active:
            user.deactivated_at = datetime.now(timezone.utc)
    if body.session_timeout_minutes is not None:
        user.session_timeout_minutes = (
            None if body.session_timeout_minutes == 0 else body.session_timeout_minutes
        )
    await db.commit()
    await db.refresh(user)
    return _user_to_read(user)


@router.delete("/admin/users/{user_id}", status_code=200)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin")),
) -> dict:
    """
    Slet bruger permanent inkl. alle tokens.
    Hvis ingen brugere er tilbage, returnerer /setup-status setup_required=True igen.
    """
    from sqlalchemy import delete as sa_delete
    from app.models.auth_token import AuthToken

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Bruger ikke fundet")

    # Slet tokens først (FK constraint)
    await db.execute(sa_delete(AuthToken).where(AuthToken.user_id == user_id))
    await db.delete(user)
    await db.commit()
    logger.info("user_deleted", user_id=str(user_id))
    return {"ok": True}
