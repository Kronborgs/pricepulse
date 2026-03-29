"""
Backup-service — eksporterer/importerer kritiske data som komprimeret JSON.
Gemmes i /app/data/backup/ (hostet: /mnt/user/appdata/pricepulse/backup/).

Backup-format version 2:
  - v1_watches       : alle Watch-objekter (inkl. scraper_config)
  - v1_price_history : fuld prishistorik for v1 watches
  - v2_watches       : ProductWatch-objekter
  - v2_watch_sources : WatchSource-objekter
  - v2_price_events  : SourcePriceEvent-objekter
  - products         : alle produkter
  - users            : aktive brugere inkl. password_hash
  - smtp_settings    : SMTP-konfiguration (uden krypteret kodeord)
"""
from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import text

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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _s(v) -> str | None:
    return str(v) if v is not None else None

def _dt(v) -> str | None:
    return v.isoformat() if v is not None else None

def _f(v) -> float | None:
    return float(v) if v is not None else None


# ─── Create backup ────────────────────────────────────────────────────────────

async def create_backup() -> str:
    """
    Lav en komplet backup (format v2) og returner filnavnet.
    Inkluderer v1 Watch + PriceHistory, v2 ProductWatch + WatchSource + SourcePriceEvent,
    Produkter, Brugere (inkl. password_hash) og SMTP-config.
    """
    from app.database import AsyncSessionLocal
    from app.models.watch import Watch
    from app.models.price_history import PriceHistory
    from app.models.product_watch import ProductWatch
    from app.models.watch_source import WatchSource
    from app.models.product import Product
    from app.models.shop import Shop
    from app.models.source_price_event import SourcePriceEvent
    from app.models.user import User
    from app.models.smtp_settings import SMTPSettings
    from sqlalchemy import select

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        # ─── Shops ────────────────────────────────────────────────────────────
        shops = list(
            (await db.execute(select(Shop))).scalars().all()
        )

        # ─── V1 Watches ───────────────────────────────────────────────────────
        v1_watches = list(
            (await db.execute(select(Watch))).scalars().all()
        )
        v1_watch_ids = [w.id for w in v1_watches]

        # ─── V1 Price history ─────────────────────────────────────────────────
        v1_history = list(
            (await db.execute(
                select(PriceHistory).where(PriceHistory.watch_id.in_(v1_watch_ids))
            )).scalars().all()
        ) if v1_watch_ids else []

        # ─── V2 ProductWatches ────────────────────────────────────────────────
        v2_watches = list(
            (await db.execute(
                select(ProductWatch).where(ProductWatch.status != "archived")
            )).scalars().all()
        )
        v2_watch_ids = [w.id for w in v2_watches]

        # ─── V2 WatchSources ──────────────────────────────────────────────────
        v2_sources = list(
            (await db.execute(
                select(WatchSource).where(WatchSource.watch_id.in_(v2_watch_ids))
            )).scalars().all()
        ) if v2_watch_ids else []
        v2_source_ids = [s.id for s in v2_sources]

        # ─── V2 Price events ──────────────────────────────────────────────────
        v2_events = list(
            (await db.execute(
                select(SourcePriceEvent).where(SourcePriceEvent.source_id.in_(v2_source_ids))
            )).scalars().all()
        ) if v2_source_ids else []

        # ─── Products (fra begge v1 og v2) ───────────────────────────────────
        product_ids = list(
            {w.product_id for w in v1_watches if w.product_id}
            | {w.product_id for w in v2_watches}
        )
        products = list(
            (await db.execute(
                select(Product).where(Product.id.in_(product_ids))
            )).scalars().all()
        ) if product_ids else []

        # ─── Brugere ──────────────────────────────────────────────────────────
        users = list(
            (await db.execute(select(User).where(User.is_active == True))).scalars().all()  # noqa: E712
        )

        # ─── SMTP ─────────────────────────────────────────────────────────────
        smtp_rows = list(
            (await db.execute(select(SMTPSettings))).scalars().all()
        )

    payload: dict = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "version": 2,
        "shops": [
            {
                "id": _s(s.id),
                "name": s.name,
                "domain": s.domain,
                "logo_url": s.logo_url,
                "default_provider": s.default_provider,
                "default_price_selector": s.default_price_selector,
                "default_title_selector": s.default_title_selector,
                "default_stock_selector": s.default_stock_selector,
                "is_active": s.is_active,
                "created_at": _dt(s.created_at),
            }
            for s in shops
        ],
        "products": [
            {
                "id": _s(p.id),
                "name": p.name,
                "brand": p.brand,
                "model": p.model,
                "variant": p.variant,
                "mpn": p.mpn,
                "ean": p.ean,
                "description": p.description,
                "image_url": p.image_url,
                "status": p.status,
                "is_active": p.is_active,
                "created_at": _dt(p.created_at),
            }
            for p in products
        ],
        # ── V1 ────────────────────────────────────────────────────────────────
        "v1_watches": [
            {
                "id": _s(w.id),
                "product_id": _s(w.product_id),
                "shop_id": _s(w.shop_id),
                "url": w.url,
                "title": w.title,
                "image_url": w.image_url,
                "current_price": _f(w.current_price),
                "current_currency": w.current_currency,
                "current_stock_status": w.current_stock_status,
                "status": w.status,
                "check_interval": w.check_interval,
                "provider": w.provider,
                "scraper_config": w.scraper_config,
                "is_active": w.is_active,
                "created_at": _dt(w.created_at),
            }
            for w in v1_watches
        ],
        "v1_price_history": [
            {
                "id": h.id,
                "watch_id": _s(h.watch_id),
                "price": _f(h.price),
                "currency": h.currency,
                "stock_status": h.stock_status,
                "recorded_at": _dt(h.recorded_at),
                "is_change": h.is_change,
            }
            for h in v1_history
        ],
        # ── V2 ────────────────────────────────────────────────────────────────
        "v2_watches": [
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
            for w in v2_watches
        ],
        "v2_watch_sources": [
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
                "consecutive_errors": s.consecutive_errors,
                "created_at": _dt(s.created_at),
            }
            for s in v2_sources
        ],
        "v2_price_events": [
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
            for e in v2_events
        ],
        # ── Brugere & SMTP ────────────────────────────────────────────────────
        "users": [
            {
                "id": _s(u.id),
                "email": u.email,
                "password_hash": u.password_hash,
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
                # password_enc udelades — skal genindtastes i UI (Fernet-nøgle kan skifte)
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

    total_history = len(v1_history) + len(v2_events)
    logger.info(
        "Backup oprettet (v2)",
        filename=filename,
        products=len(products),
        v1_watches=len(v1_watches),
        v1_history=len(v1_history),
        v2_watches=len(v2_watches),
        v2_sources=len(v2_sources),
        v2_events=len(v2_events),
    )
    return filename


# ─── Restore ──────────────────────────────────────────────────────────────────

async def restore_from_backup(filepath: Path, import_users: bool = True) -> dict:
    """
    Gendan fra en backup-fil (v1 eller v2 format).
    Bruger UPSERT — dvs. eksisterende poster opdateres, nye indsættes.
    Returnerer en dict med antal gendannede poster pr. tabel.
    """
    with gzip.open(filepath, "rt", encoding="utf-8") as fh:
        data = json.load(fh)

    version = data.get("version", 1)
    stats: dict[str, int] = {}

    from app.database import AsyncSessionLocal
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import text as sa_text

    from app.models.product import Product
    from app.models.shop import Shop
    from app.models.watch import Watch
    from app.models.price_history import PriceHistory
    from app.models.product_watch import ProductWatch
    from app.models.watch_source import WatchSource
    from app.models.source_price_event import SourcePriceEvent
    from app.models.user import User
    from app.models.smtp_settings import SMTPSettings

    def _uuid(v) -> str | None:
        return str(v) if v else None

    def _parse_dt(v):
        from datetime import datetime
        if v is None:
            return None
        try:
            return datetime.fromisoformat(v)
        except Exception:
            return None

    async with AsyncSessionLocal() as db:

        # ── Shops (skal gendannes FØR watches pga. FK) ────────────────────────
        shops_data = data.get("shops", [])
        for row in shops_data:
            stmt = pg_insert(Shop).values(
                id=row["id"],
                name=row["name"],
                domain=row["domain"],
                logo_url=row.get("logo_url"),
                default_provider=row.get("default_provider", "http"),
                default_price_selector=row.get("default_price_selector"),
                default_title_selector=row.get("default_title_selector"),
                default_stock_selector=row.get("default_stock_selector"),
                is_active=row.get("is_active", True),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={"name": row["name"], "logo_url": row.get("logo_url"), "is_active": row.get("is_active", True)},
            )
            await db.execute(stmt)
        stats["shops"] = len(shops_data)
        # Set af kendte shop-IDs — bruges til at sætte shop_id=NULL hvis shop mangler i backup
        known_shop_ids = {row["id"] for row in shops_data}

        # ── Products ──────────────────────────────────────────────────────────
        products_data = data.get("products", [])
        for row in products_data:
            stmt = pg_insert(Product).values(
                id=row["id"],
                name=row["name"],
                brand=row.get("brand"),
                model=row.get("model"),
                variant=row.get("variant"),
                mpn=row.get("mpn"),
                ean=row.get("ean"),
                description=row.get("description"),
                image_url=row.get("image_url"),
                status=row.get("status", "active"),
                is_active=row.get("is_active", True),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={"name": row["name"], "brand": row.get("brand"), "ean": row.get("ean"), "image_url": row.get("image_url")},
            )
            await db.execute(stmt)
        stats["products"] = len(products_data)

        # ── V1 Watches ────────────────────────────────────────────────────────
        v1_watches_data = data.get("v1_watches", data.get("watches", []))  # compat v1 format
        for row in v1_watches_data:
            # Sæt shop_id=NULL hvis shop ikke er i backup (ældre backup-format eller shop slettet)
            raw_shop_id = row.get("shop_id")
            shop_id = raw_shop_id if (raw_shop_id and raw_shop_id in known_shop_ids) else None
            stmt = pg_insert(Watch).values(
                id=row["id"],
                product_id=row.get("product_id"),
                shop_id=shop_id,
                url=row["url"],
                title=row.get("title"),
                image_url=row.get("image_url"),
                current_price=row.get("current_price"),
                current_currency=row.get("current_currency", "DKK"),
                current_stock_status=row.get("current_stock_status"),
                status=row.get("status", "active"),
                check_interval=row.get("check_interval", 60),
                provider=row.get("provider", "curl_cffi"),
                scraper_config=row.get("scraper_config"),
                is_active=row.get("is_active", True),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "url": row["url"],
                    "title": row.get("title"),
                    "current_price": row.get("current_price"),
                    "current_stock_status": row.get("current_stock_status"),
                    "scraper_config": row.get("scraper_config"),
                },
            )
            await db.execute(stmt)
        stats["v1_watches"] = len(v1_watches_data)

        # ── V1 Price History ──────────────────────────────────────────────────
        history_data = data.get("v1_price_history", [])
        inserted_hist = 0
        for row in history_data:
            stmt = pg_insert(PriceHistory).values(
                id=row["id"],
                watch_id=row["watch_id"],
                price=row.get("price"),
                currency=row.get("currency", "DKK"),
                stock_status=row.get("stock_status"),
                recorded_at=_parse_dt(row.get("recorded_at")),
                is_change=row.get("is_change", False),
            ).on_conflict_do_nothing(index_elements=["id"])
            await db.execute(stmt)
            inserted_hist += 1
        if history_data:
            # Opdater sequence så næste auto-increment ikke kolliderer
            await db.execute(sa_text(
                "SELECT setval('price_history_id_seq', "
                "COALESCE((SELECT MAX(id) FROM price_history), 1), true)"
            ))
        stats["v1_price_history"] = inserted_hist

        # ── V2 ProductWatches ─────────────────────────────────────────────────
        v2_watches_data = data.get("v2_watches", [])
        for row in v2_watches_data:
            stmt = pg_insert(ProductWatch).values(
                id=row["id"],
                product_id=row["product_id"],
                owner_id=row.get("owner_id"),
                name=row.get("name"),
                status=row.get("status", "active"),
                default_interval_min=row.get("default_interval_min", 60),
                last_best_price=row.get("last_best_price"),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={"status": row.get("status", "active"), "last_best_price": row.get("last_best_price")},
            )
            await db.execute(stmt)
        stats["v2_watches"] = len(v2_watches_data)

        # ── V2 WatchSources ───────────────────────────────────────────────────
        v2_sources_data = data.get("v2_watch_sources", data.get("watch_sources", []))
        for row in v2_sources_data:
            stmt = pg_insert(WatchSource).values(
                id=row["id"],
                watch_id=row["watch_id"],
                shop=row["shop"],
                url=row["url"],
                previous_url=row.get("previous_url"),
                status=row.get("status", "active"),
                interval_override_min=row.get("interval_override_min"),
                last_price=row.get("last_price"),
                last_currency=row.get("last_currency", "DKK"),
                last_stock_status=row.get("last_stock_status"),
                scraper_config=row.get("scraper_config"),
                provider=row.get("provider", "curl_cffi"),
                consecutive_errors=row.get("consecutive_errors", 0),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "url": row["url"],
                    "last_price": row.get("last_price"),
                    "scraper_config": row.get("scraper_config"),
                },
            )
            await db.execute(stmt)
        stats["v2_watch_sources"] = len(v2_sources_data)

        # ── V2 Price Events ───────────────────────────────────────────────────
        v2_events_data = data.get("v2_price_events", data.get("price_events", []))
        inserted_ev = 0
        for row in v2_events_data:
            stmt = pg_insert(SourcePriceEvent).values(
                id=row["id"],
                source_id=row["source_id"],
                old_price=row.get("old_price"),
                new_price=row.get("new_price"),
                old_stock=row.get("old_stock"),
                new_stock=row.get("new_stock"),
                change_type=row["change_type"],
                created_at=_parse_dt(row.get("created_at")),
            ).on_conflict_do_nothing(index_elements=["id"])
            await db.execute(stmt)
            inserted_ev += 1
        if v2_events_data:
            await db.execute(sa_text(
                "SELECT setval('source_price_events_id_seq', "
                "COALESCE((SELECT MAX(id) FROM source_price_events), 1), true)"
            ))
        stats["v2_price_events"] = inserted_ev

        # ── Brugere ───────────────────────────────────────────────────────────
        users_data = data.get("users", [])
        if import_users:
            for row in users_data:
                if not row.get("password_hash"):
                    continue  # spring brugere uden hash over (v1-backup)
                stmt = pg_insert(User).values(
                    id=row["id"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    display_name=row.get("display_name"),
                    role=row.get("role", "superuser"),
                    is_active=row.get("is_active", True),
                    email_verified=True,
                ).on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "email": row["email"],
                        "password_hash": row["password_hash"],
                        "display_name": row.get("display_name"),
                        "role": row.get("role", "superuser"),
                        "is_active": row.get("is_active", True),
                    },
                )
                await db.execute(stmt)
            stats["users"] = len([r for r in users_data if r.get("password_hash")])
        else:
            stats["users"] = 0

        # ── SMTP ──────────────────────────────────────────────────────────────
        smtp_data = data.get("smtp_settings", [])
        # SMTP gendanes kun deskriptivt (ingen kodeord) — brugeren skal genindtaste adgangskode
        stats["smtp_restored"] = len(smtp_data)

        await db.commit()

    logger.info("Restore gennemført", **stats)
    return stats
