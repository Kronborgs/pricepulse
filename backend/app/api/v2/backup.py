"""
Backup API — liste, kør, konfigurér, download og gendan backups.
Kun tilgængelig for admin-brugere.
"""
from __future__ import annotations

import re
import shutil
import tempfile

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import AdminUser
from app.services.backup_service import (
    BACKUP_DIR,
    create_backup,
    list_backups,
    load_config,
    restore_from_backup,
    save_config,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

_SAFE_FILENAME_RE = re.compile(r"^backup_[\w\-]+\.json\.gz$")


class BackupConfig(BaseModel):
    enabled: bool = False
    interval_hours: int = Field(default=24, ge=1, le=8760)
    keep_count: int = Field(default=7, ge=1, le=365)


class RestoreRequest(BaseModel):
    import_users: bool = True


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/admin/backup/list")
async def get_backup_list(_admin: AdminUser = None) -> list[dict]:
    return list_backups()


# ── Manual run ────────────────────────────────────────────────────────────────

@router.post("/admin/backup/run")
async def run_backup_now(_admin: AdminUser = None) -> dict:
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


# ── Restore from existing backup ──────────────────────────────────────────────

@router.post("/admin/backup/restore/{filename}")
async def restore_backup(
    filename: str,
    body: RestoreRequest,
    _admin: AdminUser = None,
) -> dict:
    """Gendan fra en gemt backup-fil på serveren."""
    if not _SAFE_FILENAME_RE.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Ugyldigt filnavn")
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup ikke fundet")
    try:
        stats = await restore_from_backup(filepath, import_users=body.import_users)
        return {"ok": True, "stats": stats}
    except Exception as e:
        logger.error("Restore fejlede", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── Restore from uploaded file ────────────────────────────────────────────────

@router.post("/admin/backup/upload-restore")
async def upload_and_restore(
    file: UploadFile = File(...),
    import_users: bool = True,
    _admin: AdminUser = None,
) -> dict:
    """
    Upload og gendan en backup-fil direkte.
    Bruges til 'frisk installation' — upload den gemte .json.gz-fil.
    """
    if not file.filename or not file.filename.endswith(".json.gz"):
        raise HTTPException(status_code=400, detail="Filen skal være en .json.gz backup-fil")

    # Skriv uploadet fil til en midlertidig placering
    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        from pathlib import Path
        stats = await restore_from_backup(Path(tmp_path), import_users=import_users)
        return {"ok": True, "stats": stats}
    except Exception as e:
        logger.error("Upload-restore fejlede", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/admin/backup/{filename}")
async def delete_backup(filename: str, _admin: AdminUser = None) -> dict:
    if not _SAFE_FILENAME_RE.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Ugyldigt filnavn")
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup ikke fundet")
    filepath.unlink()
    return {"ok": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_scheduler(cfg: dict) -> None:
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
            except Exception:
                pass
    except Exception as e:
        logger.warning("Kunne ikke opdatere backup-job", error=str(e))
