"""
SourceService — håndterer WatchSource CRUD og check-logik.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product_watch import ProductWatch
from app.models.source_check import SourceCheck
from app.models.source_price_event import SourcePriceEvent
from app.models.watch_source import WatchSource
from app.models.watch_timeline_event import WatchTimelineEvent
from app.scraper.engine import PLAYWRIGHT_REQUIRED_DOMAINS, scraper_engine
from app.schemas.v2 import WatchSourceCreate, WatchSourceUpdate
logger = structlog.get_logger(__name__)

# Backoff-tabel: (consecutive_errors_min, multiplier, max_minutes)
_BACKOFF_TABLE = [
    (0, 1, None),
    (3, 2, 240),
    (5, 4, 480),
]
ERROR_THRESHOLD = 10   # source → 'error' efter dette antal fejl


class SourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Opret ─────────────────────────────────────────────────────────────────

    async def add_source(
        self,
        watch: ProductWatch,
        data: WatchSourceCreate,
    ) -> WatchSource:
        domain = urlparse(data.url).netloc.lower().removeprefix("www.")
        provider = data.provider
        if domain in PLAYWRIGHT_REQUIRED_DOMAINS:
            provider = "playwright"

        source = WatchSource(
            watch_id=watch.id,
            shop=domain,
            url=data.url,
            status="pending",
            interval_override_min=data.interval_override_min,
            provider=provider,
            scraper_config=data.scraper_config,
            next_check_at=datetime.now(timezone.utc),  # klar til straks
        )
        self.db.add(source)

        event = WatchTimelineEvent(
            watch_id=watch.id,
            event_type="source_added",
            event_data={"url": data.url, "shop": domain},
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(source)
        logger.info("Source tilføjet", source_id=str(source.id), url=data.url)
        return source

    # ── Opdatér ───────────────────────────────────────────────────────────────

    async def update_source(
        self, source: WatchSource, data: WatchSourceUpdate
    ) -> WatchSource:
        update_fields = data.model_dump(exclude_unset=True, exclude={"url"})

        # URL-ændring håndteres særskilt
        if data.url and data.url != source.url:
            new_domain = urlparse(data.url).netloc.lower().removeprefix("www.")
            old_url = source.url

            if new_domain != source.shop:
                # Nyt domæne → gem gammel URL som previous_url + log det
                source.previous_url = old_url
                source.shop = new_domain
                event_type = "source_url_changed"
            else:
                # Samme domæne (lille ændring)
                source.previous_url = old_url
                event_type = "source_url_changed"

            source.url = data.url
            self.db.add(WatchTimelineEvent(
                watch_id=source.watch_id,
                source_id=source.id,
                event_type=event_type,
                event_data={"old_url": old_url, "new_url": data.url},
            ))

        for field, value in update_fields.items():
            setattr(source, field, value)

        await self.db.commit()
        await self.db.refresh(source)
        return source

    # ── Pause / resume ────────────────────────────────────────────────────────

    async def pause_source(self, source: WatchSource) -> WatchSource:
        if source.status == "archived":
            return source
        source.status = "paused"
        source.paused_at = datetime.now(timezone.utc)
        source.next_check_at = None
        self.db.add(WatchTimelineEvent(
            watch_id=source.watch_id,
            source_id=source.id,
            event_type="source_paused",
        ))
        await self.db.commit()
        await self.db.refresh(source)
        await self._update_watch_status(source.watch_id)
        return source

    async def resume_source(self, source: WatchSource) -> WatchSource:
        if source.status == "archived":
            return source
        source.status = "active"
        source.paused_at = None
        source.next_check_at = datetime.now(timezone.utc)
        self.db.add(WatchTimelineEvent(
            watch_id=source.watch_id,
            source_id=source.id,
            event_type="source_resumed",
        ))
        await self.db.commit()
        await self.db.refresh(source)
        await self._update_watch_status(source.watch_id)
        return source

    async def archive_source(self, source: WatchSource) -> WatchSource:
        source.status = "archived"
        source.archived_at = datetime.now(timezone.utc)
        source.next_check_at = None
        self.db.add(WatchTimelineEvent(
            watch_id=source.watch_id,
            source_id=source.id,
            event_type="source_archived",
        ))
        await self.db.commit()
        await self.db.refresh(source)
        await self._update_watch_status(source.watch_id)
        return source

    # ── Watch pause / resume ──────────────────────────────────────────────────

    async def pause_watch(self, watch: ProductWatch) -> ProductWatch:
        watch.status = "paused"
        watch.paused_at = datetime.now(timezone.utc)
        self.db.add(WatchTimelineEvent(
            watch_id=watch.id,
            event_type="watch_paused",
        ))
        await self.db.commit()
        await self.db.refresh(watch)
        return watch

    async def resume_watch(self, watch: ProductWatch) -> ProductWatch:
        watch.status = "active"
        watch.paused_at = None
        self.db.add(WatchTimelineEvent(
            watch_id=watch.id,
            event_type="watch_resumed",
        ))
        await self.db.commit()
        await self.db.refresh(watch)
        # Sæt aktive sources klar til check
        stmt = select(WatchSource).where(
            WatchSource.watch_id == watch.id,
            WatchSource.status == "active",
        )
        sources = (await self.db.execute(stmt)).scalars().all()
        for s in sources:
            s.next_check_at = datetime.now(timezone.utc)
        await self.db.commit()
        return watch

    # ── Check (kernes scrape-flow for WatchSource) ────────────────────────────

    async def run_check(self, source_id: uuid.UUID) -> None:
        """Hent og ekstrakt pris for én source. Kaldes af scheduler."""
        from types import SimpleNamespace

        stmt = (
            select(WatchSource)
            .where(WatchSource.id == source_id)
            .options(selectinload(WatchSource.watch))
        )
        source = (await self.db.execute(stmt)).scalar_one_or_none()
        if not source or source.status not in ("active", "pending"):
            return

        watch = source.watch
        if watch.status in ("paused", "archived"):
            return

        # Byg fake-watch objekt til scraper_engine (v1-kompatibelt interface)
        fake_watch = SimpleNamespace(
            id=source.id,
            url=source.url,
            scraper_config=source.scraper_config,
            shop=SimpleNamespace(domain=source.shop) if source.shop else None,
            provider=source.provider,
        )

        scrape_result, parse_result = await scraper_engine.scrape(fake_watch)

        now = datetime.now(timezone.utc)
        source.last_check_at = now

        # Afgør fejltype — parser_mismatch sendes til sekventiel Ollama-kø
        error_type = (scrape_result.diagnostic or {}).get("error_type") if not scrape_result.success else None
        ollama_queued = False

        if not scrape_result.success and scrape_result.fetch_ok and scrape_result.html_snippet and error_type == "parser_mismatch":
            from app.services.ollama_queue import OllamaJob, enqueue as ollama_enqueue
            ollama_enqueue(OllamaJob(
                entity_type="source",
                entity_id=source.id,
                url=source.url,
                html_snippet=scrape_result.html_snippet,
                extractors_tried=(parse_result.extractors_tried or []) if parse_result else [],
                status_code=scrape_result.status_code,
                scraper_config=source.scraper_config,
                diagnostic=scrape_result.diagnostic,
                previous_status=source.status,
            ))
            # Sæt midlertidig status og næste check (undgår gentagelse mens kø behandler)
            source.status = "ai_analyzing"
            interval = source.interval_override_min or watch.default_interval_min
            source.next_check_at = now + timedelta(minutes=max(interval, 30))
            ollama_queued = True

        if not ollama_queued:
            if scrape_result.success and parse_result:
                await self._process_success(source, parse_result, scrape_result.diagnostic, now)
            else:
                await self._process_failure(source, scrape_result, now)

            # Sæt næste check-tid
            interval = source.interval_override_min or watch.default_interval_min
            source.next_check_at = now + timedelta(minutes=interval)
            source.status = "active" if scrape_result.success else source.status

        await self.db.commit()

        # Opdatér watch-aggregater
        await self._update_watch_best_price(watch.id)
        await self._update_watch_status(watch.id)

    async def _process_success(
        self, source: WatchSource, parse_result, diagnostic: dict | None, now: datetime
    ) -> None:
        new_price = float(parse_result.price) if parse_result.price is not None else None
        new_stock = parse_result.stock_status
        old_price = float(source.last_price) if source.last_price is not None else None
        old_stock = source.last_stock_status
        is_initial = source.last_check_at is None or source.status == "pending"

        price_changed = old_price is not None and new_price != old_price
        stock_changed = old_stock != new_stock

        check = SourceCheck(
            source_id=source.id,
            checked_at=now,
            price=new_price,
            currency=parse_result.currency or "DKK",
            stock_status=new_stock,
            success=True,
            status_code=diagnostic.get("fetch", {}).get("status_code") if diagnostic else None,
            response_time_ms=diagnostic.get("fetch", {}).get("response_time_ms") if diagnostic else None,
            html_length=diagnostic.get("fetch", {}).get("html_length") if diagnostic else None,
            extractor_used=diagnostic.get("parse", {}).get("extractor") if diagnostic else None,
            is_price_change=price_changed,
            is_stock_change=stock_changed,
            raw_diagnostic=diagnostic,
        )
        self.db.add(check)

        # Flush for at få check.id
        await self.db.flush()

        if is_initial or price_changed or stock_changed:
            change_type = "initial"
            if price_changed and new_price and old_price:
                change_type = "increase" if new_price > old_price else "decrease"
            elif stock_changed:
                in_stock = new_stock and ("lager" in new_stock.lower() or "stock" in new_stock.lower())
                change_type = "back_in_stock" if in_stock else "unavailable"

            event = SourcePriceEvent(
                source_id=source.id,
                check_id=check.id,
                old_price=old_price,
                new_price=new_price,
                old_stock=old_stock,
                new_stock=new_stock,
                change_type=change_type,
            )
            self.db.add(event)

            if is_initial:
                self.db.add(WatchTimelineEvent(
                    watch_id=source.watch_id,
                    source_id=source.id,
                    event_type="first_price_found",
                    event_data={"price": new_price, "stock": new_stock},
                ))

            # Kø øjeblikkelig notifikation (kun hvis ikke initial)
            if not is_initial:
                await self._dispatch_notification(source, event, new_stock)

        # Opdatér source
        source.last_price = new_price
        source.last_currency = parse_result.currency or "DKK"
        source.last_stock_status = new_stock
        source.last_diagnostic = diagnostic
        source.consecutive_errors = 0
        source.last_error_type = None
        source.last_error_message = None

    async def _process_failure(
        self, source: WatchSource, scrape_result, now: datetime
    ) -> None:
        diagnostic = scrape_result.diagnostic or {}
        error_type = diagnostic.get("error_type", "unknown")
        bot_suspected = error_type in ("bot_protection", "challenge_page_detected", "rate_limited")

        if bot_suspected and not source.bot_suspected_at:
            source.bot_suspected_at = now
            self.db.add(WatchTimelineEvent(
                watch_id=source.watch_id,
                source_id=source.id,
                event_type="bot_suspected",
                event_data={"error_type": error_type},
            ))

        source.consecutive_errors += 1
        source.last_error_type = error_type
        source.last_error_message = scrape_result.error
        source.last_diagnostic = diagnostic

        if source.consecutive_errors >= ERROR_THRESHOLD:
            source.status = "error"
            self.db.add(WatchTimelineEvent(
                watch_id=source.watch_id,
                source_id=source.id,
                event_type="error_streak",
                event_data={"consecutive_errors": source.consecutive_errors, "error_type": error_type},
            ))
        elif bot_suspected:
            # Forlæng næste check til 6 timer
            source.next_check_at = now + timedelta(hours=6)
        else:
            # Backoff baseret på consecutive_errors
            interval = source.interval_override_min or (source.watch.default_interval_min if source.watch else 60)
            multiplier = 1
            for threshold, mult, max_min in _BACKOFF_TABLE:
                if source.consecutive_errors >= threshold:
                    multiplier = mult
            backed_off = interval * multiplier
            if max_min:
                backed_off = min(backed_off, max_min)
            source.next_check_at = now + timedelta(minutes=backed_off)

        check = SourceCheck(
            source_id=source.id,
            checked_at=now,
            success=False,
            status_code=scrape_result.status_code,
            error_type=error_type,
            error_message=scrape_result.error,
            bot_suspected=bot_suspected,
            raw_diagnostic=diagnostic,
        )
        self.db.add(check)

    # ── Aggregering ───────────────────────────────────────────────────────────

    async def _dispatch_notification(
        self, source: WatchSource, event: SourcePriceEvent, new_stock: str | None
    ) -> None:
        """
        Send øjeblikkelig e-mailnotifikation baseret på notification_rules (rule_type='instant').
        Én email pr. matchende aktiv regel.
        """
        try:
            from app.models.notification_rule import NotificationRule
            from app.models.product import Product
            from app.models.user import User
            from app.services.smtp_service import smtp_service

            watch = source.watch
            if not watch or not watch.owner_id:
                return

            change_type = event.change_type
            is_price_drop = change_type == "decrease"
            is_back_in_stock = change_type == "back_in_stock"

            user = await self.db.scalar(select(User).where(User.id == watch.owner_id))
            if not user or not user.email:
                return

            # Hent alle aktive instant-regler for denne bruger
            rules_result = await self.db.execute(
                select(NotificationRule).where(
                    NotificationRule.user_id == watch.owner_id,
                    NotificationRule.rule_type == "instant",
                    NotificationRule.enabled == True,
                )
            )
            instant_rules = rules_result.scalars().all()
            if not instant_rules:
                return

            # Hent produkt én gang
            product = await self.db.scalar(
                select(Product).where(Product.id == watch.product_id)
            )

            in_stock = bool(
                new_stock and ("lager" in new_stock.lower() or "stock" in new_stock.lower())
            )
            watch_name = watch.name or (product.name if product else f"Produkt ({str(watch.product_id)[:8]})")
            image_url = product.image_url if product else None

            notified = False
            for rule in instant_rules:
                # Kontrollér om hændelsestypen matcher regelens indstillinger
                wants = False
                if is_price_drop and watch.notify_on_price_drop and rule.notify_price_drop:
                    if watch.price_threshold and event.new_price:
                        if float(event.new_price) <= float(watch.price_threshold):
                            wants = True
                    else:
                        wants = True
                elif is_back_in_stock and watch.notify_on_back_in_stock and rule.notify_back_in_stock:
                    wants = True
                elif rule.notify_on_change and change_type in ("increase", "unavailable", "decrease", "back_in_stock"):
                    wants = True

                if not wants:
                    continue

                # Kontrollér regelens produktfilter
                filter_mode = rule.filter_mode or "all"
                if filter_mode == "tags":
                    rule_tags = set(rule.filter_tags or [])
                    product_tags = set(product.tags or []) if product else set()
                    if not (rule_tags & product_tags):
                        continue
                elif filter_mode == "products":
                    rule_products = {str(p) for p in (rule.filter_product_ids or [])}
                    if not product or str(product.id) not in rule_products:
                        continue

                await smtp_service.queue_price_drop(
                    db=self.db,
                    user_id=user.id,
                    to_email=user.email,
                    watch_name=watch_name,
                    old_price=float(event.old_price) if event.old_price else 0.0,
                    new_price=float(event.new_price) if event.new_price else 0.0,
                    currency=source.last_currency or "DKK",
                    watch_id=watch.id,
                    source_id=source.id,
                    image_url=image_url,
                    product_url=source.url,
                    in_stock=in_stock,
                )
                notified = True

            if notified:
                logger.info(
                    "notifikation_koelagt",
                    user_id=str(user.id),
                    watch_id=str(watch.id),
                    change_type=change_type,
                )
        except Exception as exc:
            # Blødlander fejl — en notifikation må ikke crashe scrape-pipelinen
            logger.error("notifikation_fejl", error=repr(exc))

    async def _try_ollama_retry(
        self,
        source: WatchSource,
        fake_watch,
        scrape_result,
        parse_result,
    ):
        """Ollama fallback i to trin:
        1. CSS-selektor-forslag → retry scrape
        2. Direkte tekst-udtræk fra HTML via LLM
        """
        from app.config import settings
        from app.services.ollama_service import OllamaService

        if not settings.ollama_enabled:
            return scrape_result, parse_result

        ollama = OllamaService()
        try:
            # Trin 1: CSS-selektor-forslag
            advice = await ollama.analyze_parser(
                db=self.db,
                url=fake_watch.url,
                html_snippet=scrape_result.html_snippet,
                html_title=(parse_result.title or "") if parse_result else "",
                status_code=scrape_result.status_code,
                failed_extractors=(parse_result.extractors_tried or []) if parse_result else [],
                source_id=str(source.id),
            )
            if advice and not (advice.price_selector and advice.confidence >= 0.5):
                logger.info("ollama_ingen_selector", source_id=str(source.id),
                            selector=advice.price_selector, confidence=advice.confidence)

            if advice:
                # Gem råd i diagnostik uanset om CSS-retry lykkes — UI viser forklaringen
                ollama_advice_dict = {
                    "reasoning": advice.reasoning,
                    "recommended_action": advice.recommended_action,
                    "price_selector": advice.price_selector,
                    "stock_selector": advice.stock_selector,
                    "requires_js": advice.requires_js,
                    "likely_bot_protection": advice.likely_bot_protection,
                    "confidence": advice.confidence,
                    "page_type": advice.page_type,
                }
                if scrape_result.diagnostic:
                    scrape_result.diagnostic["ollama_advice"] = ollama_advice_dict
                    if advice.recommended_action:
                        scrape_result.diagnostic["recommended_action"] = advice.recommended_action
                    if advice.requires_js and scrape_result.diagnostic.get("error_type") == "parser_mismatch":
                        scrape_result.diagnostic["error_type"] = "js_render_required"
                        scrape_result.diagnostic["recommended_action"] = (
                            "Aktivér Playwright-provider i source-indstillinger (Ollama: siden kræver JS-rendering)"
                        )

            if advice and advice.price_selector and advice.confidence >= 0.5:
                logger.info("ollama_css_forslag", source_id=str(source.id),
                            selector=advice.price_selector, confidence=advice.confidence)
                new_config = {
                    **(fake_watch.scraper_config or {}),
                    "price_selector": advice.price_selector,
                    **({"stock_selector": advice.stock_selector} if advice.stock_selector else {}),
                }
                fake_watch.scraper_config = new_config
                source.scraper_config = new_config
                retry_result, retry_parse = await scraper_engine.scrape(fake_watch)
                if retry_result.success and retry_parse:
                    return retry_result, retry_parse
                # CSS fejlede også — nulstil
                source.scraper_config = (
                    {k: v for k, v in (source.scraper_config or {}).items()
                     if k not in ("price_selector", "stock_selector")} or None
                )

            # Trin 2: Direkte tekst-udtræk
            text_result = await ollama.extract_price_from_text(
                db=self.db,
                url=fake_watch.url,
                html=scrape_result.html_snippet,
                source_id=str(source.id),
            )
            if text_result and text_result.success:
                logger.info("ollama_tekst_udtræk", source_id=str(source.id), price=text_result.price)
                # Indpak i ScrapeResult-lignende objekt
                from types import SimpleNamespace
                ok_result = SimpleNamespace(
                    success=True,
                    fetch_ok=True,
                    status_code=scrape_result.status_code,
                    diagnostic=scrape_result.diagnostic,
                    html_snippet=None,
                    error=None,
                )
                return ok_result, text_result

        except Exception as exc:
            logger.warning("ollama_retry_fejl", source_id=str(source.id), error=str(exc))
            source.scraper_config = (
                {k: v for k, v in (source.scraper_config or {}).items()
                 if k not in ("price_selector", "stock_selector")} or None
            )
        finally:
            await ollama.close()
        return scrape_result, parse_result

    # ── Aggregering ───────────────────────────────────────────────────────────

    async def _update_watch_best_price(self, watch_id: uuid.UUID) -> None:
        """Find laveste pris på tværs af aktive sources og gem på watch."""
        stmt = select(WatchSource).where(
            WatchSource.watch_id == watch_id,
            WatchSource.status.in_(["active", "pending", "ai_active"]),
            WatchSource.last_price.isnot(None),
        )
        sources = (await self.db.execute(stmt)).scalars().all()
        if not sources:
            return

        best = min(sources, key=lambda s: float(s.last_price))
        stmt_w = select(ProductWatch).where(ProductWatch.id == watch_id)
        watch = (await self.db.execute(stmt_w)).scalar_one_or_none()
        if watch:
            watch.last_best_price = best.last_price
            watch.last_best_source_id = best.id
            watch.last_checked_at = datetime.now(timezone.utc)

    async def _update_watch_status(self, watch_id: uuid.UUID) -> None:
        """Beregn aggregeret watch-status fra sources."""
        stmt_w = select(ProductWatch).where(ProductWatch.id == watch_id)
        watch = (await self.db.execute(stmt_w)).scalar_one_or_none()
        if not watch or watch.status in ("paused", "archived"):
            return

        stmt_s = select(WatchSource).where(
            WatchSource.watch_id == watch_id,
            WatchSource.status != "archived",
        )
        sources = (await self.db.execute(stmt_s)).scalars().all()
        if not sources:
            return

        statuses = {s.status for s in sources}
        if statuses <= {"active", "ai_active"}:
            watch.status = "active"
        elif statuses == {"paused"}:
            watch.status = "paused"
        elif statuses == {"error"} or statuses == {"blocked"}:
            watch.status = "error"
        else:
            watch.status = "partial"

        await self.db.commit()
