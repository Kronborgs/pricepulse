"""
Admin Data API — statistik og bulk-sletning af systemdata.
Stats er tilgængelige for admin + superuser.
Bulk-sletning er kun for admin.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, SuperOrAdmin
from app.database import get_db

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _count(db: AsyncSession, model) -> int:
    result = await db.scalar(select(func.count()).select_from(model))
    return result or 0


@router.get("/admin/data/stats")
async def data_stats(
    db: AsyncSession = Depends(get_db),
    _user: SuperOrAdmin = None,
) -> dict:
    """Returner antal poster i de vigtigste tabeller. Tilgængelig for admin + superuser."""
    from app.models.watch import Watch
    from app.models.product_watch import ProductWatch
    from app.models.product import Product
    from app.models.price_history import PriceHistory
    from app.models.source_price_event import SourcePriceEvent
    from app.models.ai_job import AIJob
    from app.models.email_queue import EmailQueue
    from app.models.source_check import SourceCheck
    from app.models.user import User

    return {
        "watches_v1": await _count(db, Watch),
        "watches_v2": await _count(db, ProductWatch),
        "products": await _count(db, Product),
        "price_history_v1": await _count(db, PriceHistory),
        "price_events_v2": await _count(db, SourcePriceEvent),
        "ai_jobs": await _count(db, AIJob),
        "email_queue": await _count(db, EmailQueue),
        "source_checks": await _count(db, SourceCheck),
        "users": await _count(db, User),
    }


@router.delete("/admin/data/watches")
async def delete_all_watches(
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    """Slet alle watches (v1 + v2) inkl. relaterede data."""
    from app.models.watch import Watch
    from app.models.product_watch import ProductWatch
    from app.models.price_history import PriceHistory
    from app.models.watch_timeline_event import WatchTimelineEvent
    from app.models.watch_source import WatchSource

    # Slet i rækkefølge der respekterer FK-afhængigheder
    await db.execute(delete(WatchTimelineEvent))
    await db.execute(delete(WatchSource))
    await db.execute(delete(PriceHistory))
    await db.execute(delete(Watch))
    await db.execute(delete(ProductWatch))
    await db.commit()
    logger.info("admin_delete_all_watches")
    return {"ok": True, "deleted": "watches"}


@router.delete("/admin/data/products")
async def delete_all_products(
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    """Slet alle produkter inkl. snapshots."""
    from app.models.product import Product
    from app.models.product_snapshot import ProductSnapshot

    await db.execute(delete(ProductSnapshot))
    await db.execute(delete(Product))
    await db.commit()
    logger.info("admin_delete_all_products")
    return {"ok": True, "deleted": "products"}


@router.delete("/admin/data/price-history")
async def delete_all_price_history(
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    """Slet al prishistorik (v1 price_history + v2 source_price_events + source_checks)."""
    from app.models.price_history import PriceHistory
    from app.models.source_price_event import SourcePriceEvent
    from app.models.source_check import SourceCheck

    await db.execute(delete(SourcePriceEvent))
    await db.execute(delete(SourceCheck))
    await db.execute(delete(PriceHistory))
    await db.commit()
    logger.info("admin_delete_all_price_history")
    return {"ok": True, "deleted": "price-history"}


@router.delete("/admin/data/ai-jobs")
async def delete_all_ai_jobs(
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    """Slet alle AI jobs og LLM-analyseresultater."""
    from app.models.ai_job import AIJob
    from app.models.llm_analysis_result import LLMAnalysisResult

    await db.execute(delete(LLMAnalysisResult))
    await db.execute(delete(AIJob))
    await db.commit()
    logger.info("admin_delete_all_ai_jobs")
    return {"ok": True, "deleted": "ai-jobs"}


@router.delete("/admin/data/email-queue")
async def delete_email_queue(
    db: AsyncSession = Depends(get_db),
    _user: AdminUser = None,
) -> dict:
    """Slet alle ventende emails fra køen."""
    from app.models.email_queue import EmailQueue

    await db.execute(delete(EmailQueue))
    await db.commit()
    logger.info("admin_delete_email_queue")
    return {"ok": True, "deleted": "email-queue"}
