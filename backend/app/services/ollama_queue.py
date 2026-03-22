"""ollama_queue.py — Sekventiel asyncio-kø til Ollama-analyse af parser-fejl.

Watches (v1) og WatchSources (v2) der fejler med parser_mismatch lægges i køen
via enqueue(). process_queue_forever() kører som asyncio-baggrundstask og
behandler ét job ad gangen — sætter status → 'ai_active' ved succes.

Flow:
  1. Scheduler kører normal scrape (json_ld / shop-parser / inline_json)
  2. Ved parser_mismatch: enqueue(job)  — ingen fejltælling endnu
  3. Queue-worker: sæt status = 'ai_analyzing', kør Ollama
  4. Succes  → gem pris, status = 'ai_active'
  5. Fejl    → gendannels 'previous_status', tæl som normal fejl
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import structlog

logger = structlog.get_logger()


@dataclass
class OllamaJob:
    entity_type: str            # "source" | "watch"
    entity_id: uuid.UUID
    url: str
    html_snippet: str
    extractors_tried: list[str] = field(default_factory=list)
    status_code: int = 200
    scraper_config: dict | None = None
    diagnostic: dict | None = None
    previous_status: str = "pending"


_queue: asyncio.Queue[OllamaJob] = asyncio.Queue()


def enqueue(job: OllamaJob) -> None:
    """Tilføj job til Ollama-køen (non-blocking)."""
    _queue.put_nowait(job)
    logger.info(
        "ollama_queued",
        entity_type=job.entity_type,
        entity_id=str(job.entity_id),
        url=job.url,
        queue_size=_queue.qsize(),
    )


async def process_queue_forever() -> None:
    """
    Kør som asyncio-baggrundstask (startes i main.py lifespan).
    Behandler ét Ollama-job ad gangen for at undgå overbelastning.
    """
    logger.info("ollama_queue_worker_starter")
    while True:
        job = await _queue.get()
        try:
            logger.info(
                "ollama_queue_behandler",
                entity_type=job.entity_type,
                entity_id=str(job.entity_id),
                url=job.url,
            )
            if job.entity_type == "source":
                await _run_source_job(job)
            else:
                await _run_watch_job(job)
        except Exception as exc:
            logger.warning(
                "ollama_queue_job_fejl",
                entity_type=job.entity_type,
                entity_id=str(job.entity_id),
                error=str(exc),
            )
        finally:
            _queue.task_done()


# ── v2 WatchSource ────────────────────────────────────────────────────────────

async def _run_source_job(job: OllamaJob) -> None:
    """Kør Ollama-analyse for en WatchSource og gem resultatet."""
    import time
    from types import SimpleNamespace

    from app.database import AsyncSessionLocal
    from app.models.watch_source import WatchSource
    from app.services.ai_job_service import AIJobService
    from app.services.source_service import SourceService

    async with AsyncSessionLocal() as db:
        svc = SourceService(db)
        ai_svc = AIJobService(db)
        source = await db.get(WatchSource, job.entity_id)
        if not source or source.status in ("archived", "paused"):
            return

        # Opret AI-job audit log
        ai_job = await ai_svc.create(
            job_type="parser_advice",
            source_id=source.id,
            watch_id=source.watch_id,
            prompt_summary=f"Parser-analyse for {source.shop}: {source.url[:100]}",
            input_data={
                "url": source.url,
                "shop": source.shop,
                "extractors_tried": job.extractors_tried,
                "status_code": job.status_code,
            },
        )

        source.status = "ai_analyzing"
        await db.commit()

        from app.config import settings
        await ai_svc.mark_processing(ai_job.id, settings.ollama_parser_model)

        fake_watch = SimpleNamespace(
            id=source.id,
            url=source.url,
            scraper_config=job.scraper_config or source.scraper_config,
            shop=SimpleNamespace(domain=source.shop) if source.shop else None,
            provider=source.provider,
        )
        fake_scrape = SimpleNamespace(
            success=False,
            fetch_ok=True,
            html_snippet=job.html_snippet,
            status_code=job.status_code,
            diagnostic=job.diagnostic,
            error=None,
        )

        now = datetime.now(timezone.utc)
        restore_status = (
            job.previous_status
            if job.previous_status != "ai_analyzing"
            else "pending"
        )

        t0 = time.monotonic()
        try:
            result, parse_result = await svc._try_ollama_retry(
                source, fake_watch, fake_scrape, None
            )
            duration_ms = int((time.monotonic() - t0) * 1000)

            if result.success and parse_result:
                await svc._process_success(source, parse_result, result.diagnostic, now)
                source.status = "ai_active"
                await ai_svc.mark_completed(
                    ai_job.id,
                    output_data={"price": parse_result.price, "stock": parse_result.stock_status},
                    summary=f"Fandt pris {parse_result.price} via AI-parser",
                    duration_ms=duration_ms,
                )
                logger.info("ollama_queue_succes", source_id=str(source.id), price=parse_result.price)
            else:
                source.status = restore_status
                await ai_svc.mark_completed(
                    ai_job.id,
                    output_data=None,
                    summary="AI fandt ingen pris",
                    duration_ms=duration_ms,
                )
                logger.info("ollama_queue_ingen_pris", source_id=str(source.id))

            source.last_check_at = now
            await db.commit()
            await svc._update_watch_best_price(source.watch_id)
            await svc._update_watch_status(source.watch_id)

        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            await ai_svc.mark_failed(ai_job.id, str(exc))
            source.status = restore_status
            await db.commit()
            raise


# ── v1 Watch ──────────────────────────────────────────────────────────────────

async def _run_watch_job(job: OllamaJob) -> None:
    """Kør Ollama-analyse for en legacy v1 Watch og gem resultatet."""
    import time
    from types import SimpleNamespace

    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.watch import Watch
    from app.services.watch_service import WatchService
    from app.services.ai_job_service import AIJobService

    async with AsyncSessionLocal() as db:
        svc = WatchService(db)
        ai_svc = AIJobService(db)
        stmt = select(Watch).where(Watch.id == job.entity_id)
        watch = (await db.execute(stmt)).scalar_one_or_none()
        if not watch or not watch.is_active:
            return

        # Opret AI-job audit log
        ai_job = await ai_svc.create(
            job_type="parser_advice",
            watch_id=watch.id,
            prompt_summary=f"Parser-analyse (v1) for {watch.url[:100]}",
            input_data={
                "url": watch.url,
                "extractors_tried": job.extractors_tried,
                "status_code": job.status_code,
            },
        )

        from app.config import settings
        await ai_svc.mark_processing(ai_job.id, settings.ollama_parser_model)

        # Sæt previous_status tilbage så _try_ollama_retry fanger den korrekte prev
        restore_status = (
            job.previous_status
            if job.previous_status != "ai_analyzing"
            else "pending"
        )
        watch.status = restore_status
        await db.commit()

        fake_scrape = SimpleNamespace(
            success=False,
            fetch_ok=True,
            html_snippet=job.html_snippet,
            status_code=job.status_code,
            diagnostic=job.diagnostic,
            error=None,
        )

        t0 = time.monotonic()
        try:
            # _try_ollama_retry: sætter watch.status = 'ai_analyzing' under kørsel,
            # gendanner til prev_status (= restore_status) ved fejl, eller lader
            # process_scraped_data sætte 'active' ved succes.
            success = await svc._try_ollama_retry(watch, fake_scrape, None)
            duration_ms = int((time.monotonic() - t0) * 1000)

            if success is True:
                # Overskriv 'active' → 'ai_active' for at markere AI-fundet pris
                watch.status = "ai_active"
                await db.commit()
                await ai_svc.mark_completed(
                    ai_job.id,
                    summary="AI fandt pris (v1 watch)",
                    duration_ms=duration_ms,
                )
            else:
                await ai_svc.mark_completed(
                    ai_job.id,
                    summary="AI fandt ingen pris (v1 watch)",
                    duration_ms=duration_ms,
                )
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            await ai_svc.mark_failed(ai_job.id, str(exc))
            raise
