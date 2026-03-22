from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None
# Alias eksponeret til andre moduler (fx main.py)
scheduler: AsyncIOScheduler | None = None


async def start_scheduler() -> None:
    global _scheduler, scheduler
    _scheduler = AsyncIOScheduler(timezone="Europe/Copenhagen")
    scheduler = _scheduler
    _scheduler.add_job(
        run_due_watches,
        trigger=IntervalTrigger(minutes=1),
        id="check_due_watches",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Scheduler startet")


async def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stoppet")


async def run_due_watches() -> None:
    """
    Køres hvert minut.
    1. Kør v2 WatchSource checks (next_check_at-baseret)
    2. Kør v1 Watch checks som fallback (backwards compat)
    """
    await _run_v2_sources()
    await _run_v1_watches_legacy()


async def _run_v2_sources() -> None:
    """v2-scheduler: find WatchSources der er klar (next_check_at <= now)."""
    from app.database import AsyncSessionLocal
    from app.models.product_watch import ProductWatch
    from app.models.watch_source import WatchSource
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        stmt = (
            select(WatchSource)
            .join(ProductWatch, WatchSource.watch_id == ProductWatch.id)
            .where(
                WatchSource.status.in_(["active", "pending", "ai_active"]),
                ProductWatch.status.not_in(["paused", "archived"]),
                WatchSource.next_check_at <= now,
            )
            .order_by(WatchSource.next_check_at.asc())
            .limit(settings.scraper_max_concurrent)
        )
        sources = list((await db.execute(stmt)).scalars().all())
        due_ids = [s.id for s in sources]

    if not due_ids:
        return

    logger.info("Kører v2 sources", count=len(due_ids))
    tasks = [asyncio.create_task(_run_source_check(sid)) for sid in due_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.error("v2 scrape-fejl", count=len(errors), first_error=str(errors[0]))


async def _run_source_check(source_id: object) -> None:
    from app.database import AsyncSessionLocal
    from app.services.source_service import SourceService

    async with AsyncSessionLocal() as db:
        svc = SourceService(db)
        await svc.run_check(source_id)


async def _run_v1_watches_legacy() -> None:
    """v1-scheduler: legacy watches der stadig ikke er migreret."""
    from app.database import AsyncSessionLocal
    from app.models.watch import Watch
    from sqlalchemy import select, or_

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        stmt = select(Watch).where(
            Watch.is_active == True,
            Watch.status.in_(["active", "pending", "ai_active"]),
            or_(
                Watch.last_checked_at == None,
                Watch.last_checked_at <= now.replace(second=0, microsecond=0),
            ),
        )
        watches = list((await db.execute(stmt)).scalars().all())

    due = []
    for w in watches:
        if w.last_checked_at is None:
            due.append(w.id)
        else:
            elapsed = (datetime.now(timezone.utc) - w.last_checked_at).total_seconds() / 60
            if elapsed >= w.check_interval:
                due.append(w.id)

    if not due:
        return

    logger.info("Kører v1 legacy watches", count=len(due))
    tasks = [asyncio.create_task(_scrape_watch(watch_id)) for watch_id in due]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.error("v1 scrape-fejl", count=len(errors), first_error=str(errors[0]))


async def _scrape_watch(watch_id: object) -> None:
    from app.services.watch_service import WatchService
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = WatchService(db)
        await service.trigger_scrape(watch_id)
