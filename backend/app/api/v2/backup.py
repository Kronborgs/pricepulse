"""
Backup API — liste, kør, konfigurér og download backups.
Kun tilgængelig for admin-brugere.
"""
from __future__ import annotations

import re

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import AdminUser
from app.services.backup_service import (
    BACKUP_DIR,
    create_backup,
    list_backups,
    load_config,
    save_config,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

_SAFE_FILENAME_RE = re.compile(r"^backup_[\w\-]+\.json\.gz$")


class BackupConfig(BaseModel):
    enabled: bool = False
    interval_hours: int = Field(default=24, ge=1, le=8760)
    keep_count: int = Field(default=7, ge=1, le=365)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/admin/backup/list")
async def get_backup_list(_admin: AdminUser = None) -> list[dict]:
    """Returner liste af gemte backupfiler, nyeste først."""
    return list_backups()


# ── Manual run ────────────────────────────────────────────────────────────────

@router.post("/admin/backup/run")
async def run_backup_now(_admin: AdminUser = None) -> dict:
    """Kør en øjeblikkelig backup."""
    try:
        filename = await create_backup()
        return {"ok": True, "filename": filename}
    except Exception as e:
        logger.error("Manuel backup fejlede", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── Config ────────────────────────────────────────────────────────────────────

@router.get("/admin/backup/config")
async def get_backup_config(_admin: AdminUser = None) -> BackupConfig:
    return BackupConfig(**load_config())


@router.put("/admin/backup/config")
async def update_backup_config(
    body: BackupConfig,
    _admin: AdminUser = None,
) -> BackupConfig:
    cfg = body.model_dump()
    save_config(cfg)
    _apply_scheduler(cfg)
    return BackupConfig(**cfg)


# ── Download ──────────────────────────────────────────────────────────────────

@router.get("/admin/backup/download/{filename}")
async def download_backup(filename: str, _admin: AdminUser = None) -> FileResponse:
    """Download én backupfil (valideret filnavn — ingen path-traversal)."""
    if not _SAFE_FILENAME_RE.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Ugyldigt filnavn")
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup ikke fundet")
    return FileResponse(
        path=str(filepath),
        media_type="application/gzip",
        filename=filename,
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/admin/backup/{filename}")
async def delete_backup(filename: str, _admin: AdminUser = None) -> dict:
    """Slet én specifik backupfil."""
    if not _SAFE_FILENAME_RE.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Ugyldigt filnavn")
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup ikke fundet")
    filepath.unlink()
    return {"ok": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_scheduler(cfg: dict) -> None:
    """Opdater APScheduler live med ny backup-konfiguration."""
    try:
        from app.scheduler.jobs import scheduler
        from apscheduler.triggers.interval import IntervalTrigger

        if not scheduler or not scheduler.running:
            return

        if cfg.get("enabled"):
            interval_h = max(1, int(cfg.get("interval_hours", 24)))
            try:
                scheduler.reschedule_job(
                    "backup_job",
                    trigger=IntervalTrigger(hours=interval_h),
                )
            except Exception:
                # Job eksisterer ikke endnu — tilføj det
                from app.scheduler.jobs import _run_scheduled_backup
                scheduler.add_job(
                    _run_scheduled_backup,
                    trigger=IntervalTrigger(hours=interval_h),
                    id="backup_job",
                    replace_existing=True,
                    max_instances=1,
                )
            logger.info("Backup-job opdateret", interval_hours=interval_h)
        else:
            try:
                scheduler.pause_job("backup_job")
                logger.info("Backup-job sat på pause")
            except Exception:
                pass
    except Exception as e:
        logger.warning("Kunne ikke opdatere backup-job", error=str(e))
