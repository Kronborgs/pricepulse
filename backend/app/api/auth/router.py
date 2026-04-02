"""
Auth API endpoints — login, logout, setup, password reset, me.
Cookies sættes som httpOnly, Secure (i prod), SameSite=Lax.
"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_optional_user
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models.user import User
from app.services.auth_service import AuthService, create_access_token

logger = structlog.get_logger(__name__)
router = APIRouter()

_SECURE = settings.cookie_secure
_SAMESITE = "lax"


# ── Schemas ───────────────────────────────────────────────────────────────────

_SPECIAL_CHARS = set("!@#$%^&*()_+-=[]{}|;':,./<>?")
_PASSWORD_EXPIRY_DAYS = 6 * 30  # ~6 måneder


def _validate_password(v: str) -> str:
    """Fælles password-styrkevalidering: min 10 tegn, stort bogstav, ciffer, specialtegn."""
    if len(v) < 10:
        raise ValueError("Kodeord skal være mindst 10 tegn")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Kodeord skal indeholde mindst ét stort bogstav")
    if not re.search(r"\d", v):
        raise ValueError("Kodeord skal indeholde mindst ét tal")
    if not any(c in _SPECIAL_CHARS for c in v):
        raise ValueError("Kodeord skal indeholde mindst ét specialtegn (!@#$%^&* osv.)")
    return v


class SetupRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    is_active: bool
    email_verified: bool
    created_at: str
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class SetupStatus(BaseModel):
    setup_required: bool


class CreateUserRequest(BaseModel):
    email: str
    password: str | None = None  # Ingen password = send invitationsmail
    role: str = "superuser"
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_password(v)
        return v


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


def _password_expired(user: User) -> bool:
    """True hvis password ikke er skiftet indenfor de seneste ~6 måneder."""
    changed_at = getattr(user, "password_changed_at", None)
    if changed_at is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=_PASSWORD_EXPIRY_DAYS)
    return changed_at < cutoff


def _user_to_read(user: User, force_must_change: bool = False) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "session_timeout_minutes": getattr(user, "session_timeout_minutes", None),
        "created_at": user.created_at.isoformat(),
        "must_change_password": force_must_change or _password_expired(user),
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


@router.post("/setup-restore")
async def setup_restore(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Gendan backup ved frisk installation.
    Kun tilladt når systemet endnu ikke er sat op (ingen brugere).
    Backup-filens brugere inkluderes altid, så gamle logins virker.
    """
    svc = AuthService(db)
    if not await svc.setup_required():
        raise HTTPException(status_code=400, detail="Systemet er allerede sat op")
    if not file.filename or not file.filename.endswith(".json.gz"):
        raise HTTPException(status_code=400, detail="Filen skal være en .json.gz backup-fil")

    # Begræns filstørrelse til 100 MB for at forhindre DoS
    MAX_UPLOAD_BYTES = 100 * 1024 * 1024
    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        received = 0
        while chunk := await file.read(65536):
            received += len(chunk)
            if received > MAX_UPLOAD_BYTES:
                tmp.close()
                import os as _os
                _os.unlink(tmp.name)
                raise HTTPException(status_code=413, detail="Fil er for stor (max 100 MB)")
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        from app.services.backup_service import restore_from_backup
        stats = await restore_from_backup(Path(tmp_path), import_users=True)
        logger.info("setup_restore_complete", stats=stats)
        return {"ok": True, "stats": stats}
    except Exception as e:
        logger.error("setup_restore_fejlede", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/login", response_model=UserRead)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Login med email + password. Sætter httpOnly cookies ved succes. Max 10 forsøg/minut pr. IP."""
    svc = AuthService(db)
    user = await svc.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forkert email eller kodeord",
        )

    expired = _password_expired(user)
    access = create_access_token(user.id, user.role)
    refresh = await svc.create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)
    return _user_to_read(user, force_must_change=expired)


@router.post("/change-password", response_model=UserRead)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Skifter password for den indloggede bruger.
    Kræver korrekt gammelt password. Udsteder nye cookies efter skift.
    """
    svc = AuthService(db)
    ok = await svc.change_password(user, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Gammelt kodeord er forkert")

    # Genindlæs brugeren (password_changed_at er nu opdateret)
    await db.refresh(user)
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
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
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
        try:
            from app.services.smtp_service import smtp_service, _app_url
            base = _app_url()
            reset_url = f"{base}/reset-password?token={raw_token}"
            body_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#f4f6f8;padding:0">
  <div style="background:#0f172a;border-radius:8px 8px 0 0;padding:20px 28px">
    <span style="font-family:sans-serif;font-size:22px;font-weight:bold;color:#29ABE2">Price</span><span style="font-family:sans-serif;font-size:22px;font-weight:bold;color:#8DC63F">Pulse</span>
  </div>
  <div style="background:#fff;padding:28px;border-radius:0 0 8px 8px;color:#1a1a1a">
    <h1 style="color:#29ABE2;margin-top:0">Nulstil dit kodeord</h1>
    <p>Klik på knappen nedenfor for at nulstille dit kodeord. Linket er gyldigt i 2 timer.</p>
    <p style="margin:24px 0">
      <a href="{reset_url}" style="display:inline-block;background:#29ABE2;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">
        Nulstil kodeord
      </a>
    </p>
    <p style="color:#aaa;font-size:12px;word-break:break-all">{reset_url}</p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0" />
    <p style="color:#999;font-size:12px;margin:0">PricePulse — automatisk prisovervågning</p>
  </div>
</body></html>"""
            await smtp_service.send_email(
                db,
                to_email=body.email,
                subject="Nulstil dit kodeord — PricePulse",
                body_html=body_html,
            )
            logger.info("password_reset_mail_sendt", email=body.email)
        except Exception as exc:
            logger.warning("forgot_password_mail_fejl", email=body.email, error=repr(exc))
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
    _caller: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin", "superuser")),
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
    _caller: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin", "superuser")),
) -> dict:
    svc = AuthService(db)
    try:
        user = await svc.create_user(
            email=body.email,
            password=body.password,  # None → tilfældig temp-kode
            role=body.role,
            display_name=body.display_name,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Send invitationsmail (med link til at sætte kodeord)
    try:
        from app.services.smtp_service import smtp_service, _app_url
        inv_token = await svc.create_invitation_token(user.id)
        base = _app_url()
        invite_url = f"{base}/reset-password?token={inv_token}&invite=1"
        display = user.display_name or user.email.split("@")[0]
        body_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#f4f6f8;padding:0">
  <div style="background:#0f172a;border-radius:8px 8px 0 0;padding:20px 28px">
    <span style="font-family:sans-serif;font-size:22px;font-weight:bold;color:#29ABE2">Price</span><span style="font-family:sans-serif;font-size:22px;font-weight:bold;color:#8DC63F">Pulse</span>
  </div>
  <div style="background:#fff;padding:28px;border-radius:0 0 8px 8px;color:#1a1a1a">
    <h1 style="color:#29ABE2;margin-top:0">Du er inviteret til PricePulse</h1>
    <p>Hej {display},</p>
    <p>Du har fået adgang til PricePulse. Klik på knappen nedenfor for at oprette dit kodeord og aktivere din konto. Linket er gyldigt i 7 dage.</p>
    <p style="margin:24px 0">
      <a href="{invite_url}" style="display:inline-block;background:#29ABE2;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">
        Opret dit kodeord
      </a>
    </p>
    <p style="color:#aaa;font-size:12px;word-break:break-all">{invite_url}</p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0" />
    <p style="color:#999;font-size:12px;margin:0">PricePulse — automatisk prisovervågning</p>
  </div>
</body></html>"""
        await smtp_service.send_email(
            db,
            to_email=user.email,
            subject="Du er inviteret til PricePulse — opret dit kodeord",
            body_html=body_html,
        )
        logger.info("invitation_mail_sendt", user_id=str(user.id))
    except Exception as exc:
        logger.warning("invitation_mail_fejl", user_id=str(user.id), error=repr(exc))

    return _user_to_read(user)


@router.patch("/admin/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin", "superuser")),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Bruger ikke fundet")
    # Superuser må kun ændre brugere med rollen 'user'
    if caller.role == "superuser" and user.role != "user":
        raise HTTPException(status_code=403, detail="Superuser kan kun ændre brugere med rollen 'user'")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        if body.role not in ("admin", "superuser", "user"):
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
    caller: User = Depends(__import__("app.api.deps", fromlist=["require_role"]).require_role("admin", "superuser")),
) -> dict:
    """
    Slet bruger permanent inkl. alle tokens.
    - admin kan slette alle brugere
    - superuser kan kun slette brugere med rollen 'user'
    Hvis ingen brugere er tilbage, returnerer /setup-status setup_required=True igen.
    """
    from sqlalchemy import delete as sa_delete
    from app.models.auth_token import AuthToken

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Bruger ikke fundet")

    # Superuser må ikke slette admin-brugere
    if caller.role == "superuser" and user.role != "user":
        raise HTTPException(status_code=403, detail="Superuser kan kun slette brugere med rollen 'user'")

    # Slet tokens først (FK constraint)
    await db.execute(sa_delete(AuthToken).where(AuthToken.user_id == user_id))
    await db.delete(user)
    await db.commit()
    logger.info("user_deleted", user_id=str(user_id))
    return {"ok": True}
