"""
Backup-service — eksporterer kritiske data til komprimeret JSON
og gemmer dem i /app/data/backup/ (hostet: /mnt/user/appdata/pricepulse/backup/).
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

BACKUP_DIR = Path("/app/data/backup")
CONFIG_FILE = Path("/app/data/backup_config.json")

_DEFAULT_CONFIG: dict = {
    "enabled": False,
    "interval_hours": 24,
    "keep_count": 7,
}


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return {**_DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return _DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ─── Listing ──────────────────────────────────────────────────────────────────

def list_backups() -> list[dict]:
    """Returnerer liste af backupfiler, nyeste først."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(BACKUP_DIR.glob("backup_*.json.gz"), reverse=True)
    result = []
    for f in files:
        stat = f.stat()
        result.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return result


def _prune_old_backups(keep_count: int) -> None:
    files = sorted(BACKUP_DIR.glob("backup_*.json.gz"), reverse=True)
    for old in files[keep_count:]:
        try:
            old.unlink()
            logger.info("Slettet gammel backup", file=old.name)
        except Exception as e:
            logger.warning("Kunne ikke slette backup", file=old.name, error=str(e))


# ─── Core backup ──────────────────────────────────────────────────────────────

async def create_backup() -> str:
    """
    Kører en komplet backup og returnerer det nye filnavn.

    Scope:
    - Alle aktive ProductWatches (status != archived)
    - Produkter tilknyttet de ovenstående watches
    - WatchSources for de aktive watches
    - SourcePriceEvents for de aktive sources
    - Alle aktive brugere (uden password_hash)
    - SMTP-konfiguration (uden krypteret kodeord)
    """
    from app.database import AsyncSessionLocal
    from app.models.product_watch import ProductWatch
    from app.models.watch_source import WatchSource
    from app.models.product import Product
    from app.models.source_price_event import SourcePriceEvent
    from app.models.user import User
    from app.models.smtp_settings import SMTPSettings
    from sqlalchemy import select

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        # 1. Aktive ProductWatches
        watches = list(
            (await db.execute(
                select(ProductWatch).where(ProductWatch.status != "archived")
            )).scalars().all()
        )
        watch_ids = [w.id for w in watches]
        product_ids = list({w.product_id for w in watches})

        # 2. Produkter
        products = list(
            (await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )).scalars().all()
        ) if product_ids else []

        # 3. WatchSources
        sources = list(
            (await db.execute(
                select(WatchSource).where(WatchSource.watch_id.in_(watch_ids))
            )).scalars().all()
        ) if watch_ids else []
        source_ids = [s.id for s in sources]

        # 4. SourcePriceEvents (prishistorik)
        events = list(
            (await db.execute(
                select(SourcePriceEvent).where(SourcePriceEvent.source_id.in_(source_ids))
            )).scalars().all()
        ) if source_ids else []

        # 5. Brugere (ingen password_hash)
        users = list(
            (await db.execute(
                select(User).where(User.is_active == True)  # noqa: E712
            )).scalars().all()
        )

        # 6. SMTP-indstillinger (ingen krypteret kodeord)
        smtp_rows = list(
            (await db.execute(select(SMTPSettings))).scalars().all()
        )

    def _s(v) -> str | None:
        return str(v) if v is not None else None

    def _dt(v) -> str | None:
        return v.isoformat() if v is not None else None

    def _f(v) -> float | None:
        return float(v) if v is not None else None

    payload: dict = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "watches": [
            {
                "id": _s(w.id),
                "product_id": _s(w.product_id),
                "owner_id": _s(w.owner_id),
                "name": w.name,
                "status": w.status,
                "default_interval_min": w.default_interval_min,
                "last_best_price": _f(w.last_best_price),
                "last_checked_at": _dt(w.last_checked_at),
                "paused_at": _dt(w.paused_at),
                "archived_at": _dt(w.archived_at),
                "created_at": _dt(w.created_at),
            }
            for w in watches
        ],
        "products": [
            {
                "id": _s(p.id),
                "name": p.name,
                "brand": p.brand,
                "ean": p.ean,
                "image_url": p.image_url,
                "created_at": _dt(p.created_at),
            }
            for p in products
        ],
        "watch_sources": [
            {
                "id": _s(s.id),
                "watch_id": _s(s.watch_id),
                "shop": s.shop,
                "url": s.url,
                "previous_url": s.previous_url,
                "status": s.status,
                "interval_override_min": s.interval_override_min,
                "last_price": _f(s.last_price),
                "last_currency": s.last_currency,
                "last_stock_status": s.last_stock_status,
                "scraper_config": s.scraper_config,
                "provider": s.provider,
                "created_at": _dt(s.created_at),
            }
            for s in sources
        ],
        "price_events": [
            {
                "id": e.id,
                "source_id": _s(e.source_id),
                "old_price": _f(e.old_price),
                "new_price": _f(e.new_price),
                "old_stock": e.old_stock,
                "new_stock": e.new_stock,
                "change_type": e.change_type,
                "created_at": _dt(e.created_at),
            }
            for e in events
        ],
        "users": [
            {
                "id": _s(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": _dt(u.created_at),
            }
            for u in users
        ],
        "smtp_settings": [
            {
                "id": s.id,
                "is_active": s.is_active,
                "host": s.host,
                "port": s.port,
                "use_tls": s.use_tls,
                "username": s.username,
                "from_email": s.from_email,
                "from_name": s.from_name,
                # Kodeord udelades bevidst — brug SMTP-opsætning i UI efter genoprettelse
            }
            for s in smtp_rows
        ],
    }

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    filename = f"backup_{now_str}.json.gz"
    filepath = BACKUP_DIR / filename

    with gzip.open(filepath, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    cfg = load_config()
    _prune_old_backups(cfg.get("keep_count", 7))

    logger.info(
        "Backup oprettet",
        filename=filename,
        watches=len(watches),
        products=len(products),
        sources=len(sources),
        events=len(events),
    )
    return filename
