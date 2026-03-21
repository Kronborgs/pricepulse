from __future__ import annotations

import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.models.watch import Watch
from app.schemas.watch import WatchCreate, WatchDetectResult
from app.scraper.engine import PLAYWRIGHT_REQUIRED_DOMAINS, scraper_engine
from app.services.price_service import PriceService

logger = structlog.get_logger()


class WatchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.price_service = PriceService(db)

    async def create_watch(self, data: WatchCreate) -> Watch:
        """Opret en ny Watch og knyt til shop automatisk."""
        shop = await self._find_or_detect_shop(data.url)

        # Bestem provider automatisk baseret på domain
        domain = urlparse(data.url).netloc.lower()
        provider = data.provider
        if domain in PLAYWRIGHT_REQUIRED_DOMAINS:
            provider = "playwright"

        watch = Watch(
            url=data.url,
            product_id=data.product_id,
            shop_id=shop.id if shop else None,
            check_interval=data.check_interval,
            provider=provider,
            scraper_config=data.scraper_config,
            status="pending",
        )

        # Arv shop-selectors hvis watch ikke har egne
        if shop and not data.scraper_config:
            watch.scraper_config = {
                k: v
                for k, v in {
                    "price_selector": shop.default_price_selector,
                    "title_selector": shop.default_title_selector,
                    "stock_selector": shop.default_stock_selector,
                }.items()
                if v
            } or None

        self.db.add(watch)
        await self.db.commit()
        await self.db.refresh(watch)
        return watch

    async def trigger_scrape(self, watch_id: uuid.UUID) -> None:
        """Udfør scrape for én Watch og gem resultatet."""
        stmt = select(Watch).where(Watch.id == watch_id)
        watch = (await self.db.execute(stmt)).scalar_one_or_none()
        if not watch or not watch.is_active:
            return

        # Backfill shop_id hvis det mangler (watches oprettet før auto-shop)
        if not watch.shop_id:
            shop = await self._find_or_detect_shop(watch.url)
            if shop:
                watch.shop_id = shop.id

        scrape_result, parse_result = await scraper_engine.scrape(watch)

        if not scrape_result.success:
            diag = scrape_result.diagnostic or {}
            logger.warning(
                "scrape_parse_fejl",
                watch_id=str(watch.id),
                url=watch.url,
                extractors=diag.get("parse", {}).get("extractors_tried", []),
                error_type=diag.get("error_type"),
                fetch_ok=scrape_result.fetch_ok,
            )

        if scrape_result.success and parse_result:
            await self.price_service.process_scraped_data(watch, parse_result, scrape_result.diagnostic)
        else:
            # parser_mismatch med HTML → kø til sekventiel Ollama-analyse
            diag = scrape_result.diagnostic or {}
            error_type = diag.get("error_type")
            if scrape_result.fetch_ok and scrape_result.html_snippet and error_type == "parser_mismatch":
                from app.services.ollama_queue import OllamaJob, enqueue as ollama_enqueue
                ollama_enqueue(OllamaJob(
                    entity_type="watch",
                    entity_id=watch.id,
                    url=watch.url,
                    html_snippet=scrape_result.html_snippet,
                    extractors_tried=(parse_result.extractors_tried or []) if parse_result else [],
                    status_code=scrape_result.status_code,
                    scraper_config=watch.scraper_config,
                    diagnostic=scrape_result.diagnostic,
                    previous_status=watch.status,
                ))
                watch.last_checked_at = datetime.now(timezone.utc)
                await self.db.commit()
                return

            await self.price_service.handle_scrape_error(
                watch,
                error=scrape_result.error or "Ukendt fejl",
                status_code=scrape_result.status_code,
                diagnostic=scrape_result.diagnostic,
            )

    async def _try_ollama_retry(
        self,
        watch: Watch,
        scrape_result,
        parse_result,
    ) -> bool | None:
        """Ollama fallback i to trin:
        1. CSS-selektor-forslag → retry scrape
        2. Direkte tekst-udtræk fra HTML via LLM
        Returnerer True ved succes, False ved fejl, None hvis Ollama var optaget (skip).
        """
        from app.config import settings
        from app.services.ollama_service import OllamaService, is_ollama_busy

        if not settings.ollama_enabled:
            return False

        # Hvis Ollama allerede kører et kald, spring over — undgår timeout-kaskade
        if is_ollama_busy():
            logger.info("ollama_skip_busy", watch_id=str(watch.id))
            return None

        ollama = OllamaService()
        prev_status = watch.status
        watch.status = "ai_analyzing"
        await self.db.commit()
        # Gem status i lokal variabel — ORM-objektet er expired efter commit
        # og lazy-load virker ikke i background-task kontekst
        _status_is_analysing = True
        try:
            # Trin 1: CSS-selektor-forslag
            advice = await ollama.analyze_parser(
                db=self.db,
                url=watch.url,
                html_snippet=scrape_result.html_snippet,
                html_title=(parse_result.title or "") if parse_result else "",
                status_code=scrape_result.status_code,
                failed_extractors=(parse_result.extractors_tried or []) if parse_result else [],
                watch_id=str(watch.id),
            )

            if advice:
                # Gem Ollama-rådgivningen i diagnostik uanset om CSS-retry lykkes —
                # så UI'en kan vise dynamisk begrundelse + anbefaling frem for
                # den statiske "Konfigurér CSS-selectors manuelt"-besked.
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
                    # Overskriv den statiske recommended_action med Ollamas dynamiske
                    if advice.recommended_action:
                        scrape_result.diagnostic["recommended_action"] = advice.recommended_action
                    # Skub requires_js-fejltype op hvis Ollama kan se det
                    if advice.requires_js and scrape_result.diagnostic.get("error_type") == "parser_mismatch":
                        scrape_result.diagnostic["error_type"] = "js_render_required"
                        scrape_result.diagnostic["recommended_action"] = (
                            "Aktivér Playwright-provider i watch-indstillinger (Ollama: siden kræver JS-rendering)"
                        )

            if advice and advice.price_selector and advice.confidence >= 0.5:
                logger.info("ollama_css_forslag", watch_id=str(watch.id),
                            selector=advice.price_selector, confidence=advice.confidence)
                watch.scraper_config = {
                    **(watch.scraper_config or {}),
                    "price_selector": advice.price_selector,
                    **({"stock_selector": advice.stock_selector} if advice.stock_selector else {}),
                }
                retry_result, retry_parse = await scraper_engine.scrape(watch)
                if retry_result.success and retry_parse:
                    await self.price_service.process_scraped_data(watch, retry_parse, retry_result.diagnostic)
                    await self.db.commit()
                    _status_is_analysing = False
                    return True
                # CSS fejlede også — nulstil config
                watch.scraper_config = (
                    {k: v for k, v in (watch.scraper_config or {}).items()
                     if k not in ("price_selector", "stock_selector")} or None
                )

            # Trin 2: Direkte tekst-udtræk fra HTML
            text_result = await ollama.extract_price_from_text(
                db=self.db,
                url=watch.url,
                html=scrape_result.html_snippet,
                watch_id=str(watch.id),
            )
            if text_result and text_result.success:
                logger.info("ollama_tekst_udtræk", watch_id=str(watch.id), price=text_result.price)
                await self.price_service.process_scraped_data(watch, text_result, scrape_result.diagnostic)
                await self.db.commit()
                _status_is_analysing = False
                return True

        except Exception as exc:
            logger.warning("ollama_retry_fejl", error=str(exc), watch_id=str(watch.id))
            watch.scraper_config = (
                {k: v for k, v in (watch.scraper_config or {}).items()
                 if k not in ("price_selector", "stock_selector")} or None
            )
        finally:
            # Nulstil status fra 'ai_analyzing' via lokal variabel (ORM-objekt måske expired)
            if _status_is_analysing:
                watch.status = prev_status
                await self.db.commit()
            await ollama.close()
        return False

    async def detect_from_url(self, url: str) -> WatchDetectResult:
        """Auto-detektér pris og titel fra URL til preview."""
        domain = urlparse(url).netloc.lower()
        suggested_provider = (
            "playwright" if domain in PLAYWRIGHT_REQUIRED_DOMAINS else "http"
        )

        parse_result = await scraper_engine.detect(url)

        return WatchDetectResult(
            url=url,
            detected_title=parse_result.title,
            detected_price=parse_result.price,
            detected_currency=parse_result.currency if parse_result.price else None,
            detected_stock=parse_result.stock_status,
            detected_image_url=parse_result.image_url,
            suggested_provider=suggested_provider,
            confidence="high" if parse_result.parser_used == "json_ld" else (
                "medium" if parse_result.success else "low"
            ),
            shop_domain=domain,
            error=parse_result.error,
        )

    async def _find_or_detect_shop(self, url: str) -> Shop | None:
        """Find eksisterende shop baseret på domain — auto-opret hvis ikke fundet."""
        domain = urlparse(url).netloc.lower()
        base_domain = domain.removeprefix("www.")

        stmt = select(Shop).where(
            Shop.domain.in_([domain, base_domain, f"www.{base_domain}"])
        )
        shop = (await self.db.execute(stmt)).scalar_one_or_none()
        if shop:
            return shop

        # Auto-opret shop fra domain-navn
        name = base_domain.rsplit(".", 1)[0].capitalize()
        shop = Shop(name=name, domain=base_domain)
        self.db.add(shop)
        await self.db.flush()
        logger.info("auto_created_shop", domain=base_domain, name=name)
        return shop
