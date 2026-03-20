from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = structlog.get_logger()

_scheduler: AsyncIOScheduler | None = None


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Europe/Copenhagen")
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
    Køres hvert minut. Finder alle watches der er klar til check
    og kører dem asynkront (begrænset af scraper_max_concurrent).
    """
    from app.database import AsyncSessionLocal
    from app.models.watch import Watch
    from sqlalchemy import select, or_

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        stmt = select(Watch).where(
            Watch.is_active == True,
            Watch.status.in_(["active", "pending"]),
            or_(
                Watch.last_checked_at == None,
                # last_checked_at + interval <= now
                Watch.last_checked_at
                <= now.replace(second=0, microsecond=0),
            ),
        )
        watches = list((await db.execute(stmt)).scalars().all())

    if not watches:
        return

    # Filtrér til kun dem der faktisk er due
    due = []
    for w in watches:
        if w.last_checked_at is None:
            due.append(w.id)
        else:
            elapsed_minutes = (
                datetime.now(timezone.utc) - w.last_checked_at
            ).total_seconds() / 60
            if elapsed_minutes >= w.check_interval:
                due.append(w.id)

    if not due:
        return

    logger.info("Kører watches", count=len(due))

    tasks = [asyncio.create_task(_scrape_watch(watch_id)) for watch_id in due]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.error("Scrape-fejl", count=len(errors), first_error=str(errors[0]))


async def _scrape_watch(watch_id: object) -> None:
    from app.services.watch_service import WatchService
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = WatchService(db)
        await service.trigger_scrape(watch_id)
