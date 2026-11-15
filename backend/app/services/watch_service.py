from __future__ import annotations

import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.models.watch import Watch
from app.schemas.watch import WatchCreate, WatchDetectResult
from app.scraper.engine import PLAYWRIGHT_REQUIRED_DOMAINS, scraper_engine
from app.services.ollama_service import OllamaService
from app.services.price_service import PriceService

logger = structlog.get_logger()


class WatchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.price_service = PriceService(db)

    async def create_watch(self, data: WatchCreate, owner_id=None) -> Watch:
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
            currency_hint=data.currency_hint if data.currency_hint and data.currency_hint != "DKK" else None,
            status="pending",
            owner_id=owner_id,
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
                from app.services.ollama_queue import OllamaJob
                from app.services.ollama_queue import enqueue as ollama_enqueue
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
                watch.last_checked_at = datetime.now(UTC)
                # Gem diagnostik nu så UI viser fejltype mens Ollama arbejder
                if scrape_result.diagnostic:
                    watch.last_diagnostic = scrape_result.diagnostic
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
        """Ollama fallback i to trin med CPU-fallback:
        1. Hurtig health-check af Ollama (5 sek timeout)
        2. CSS-selektor-forslag → retry scrape
        3. Direkte tekst-udtræk fra HTML via LLM
        4. CPU-baseret fallback (ingen AI) — kører altid som sidste udvej
        
        Returnerer True ved succes, False ved fejl, None hvis Ollama var optaget (skip).
        """
        from app.config import settings

        if not settings.ollama_enabled:
            # Ollama slået fra — brug CPU-fallback direkte
            return await self._try_cpu_fallback(watch, scrape_result, parse_result)

        # Hurtig health-check af Ollama før vi sender jobs til køen
        from app.services.ollama_service import is_ollama_busy

        # Tjek om Ollama allerede kører et kald — undgår timeout-kaskade
        if is_ollama_busy():
            logger.info("ollama_skip_busy", watch_id=str(watch.id))
            return None

        ollama = OllamaService()
        try:
            # Tjek om Ollama er tilgængelig (5 sek timeout)
            is_healthy = await ollama.check_health(db=self.db, timeout=5)
            if not is_healthy:
                logger.info("ollama_ikke_tilgængelig", watch_id=str(watch.id),
                            host=settings.ollama_host)
                # Ollama offline — brug CPU-fallback uden at vente på timeout
                return await self._try_cpu_fallback(watch, scrape_result, parse_result)

            # Ollama er online — prøv AI-assisteret parsing
            prev_status = watch.status
            watch.status = "ai_analyzing"
            await self.db.commit()
            _status_is_analysing = True
            try:
                await self._try_ollama_ai(
                    ollama=ollama, watch=watch, scrape_result=scrape_result,
                    parse_result=parse_result, prev_status=prev_status,
                )
            except Exception as ai_exc:
                logger.warning("ollama_ai_fejl, fallback til CPU",
                              watch_id=str(watch.id), error=str(ai_exc))
                # AI fejlede — prøv CPU-fallback
                return await self._try_cpu_fallback(watch, scrape_result, parse_result)

        finally:
            await ollama.close()
        return False

    async def _try_ollama_ai(
        self,
        ollama: OllamaService,
        watch: Watch,
        scrape_result,
        parse_result,
        prev_status: str,
    ):
        """Kerne AI-logic — adskilt fra health-check for renere error handling."""
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

            if advice and not (advice.price_selector and advice.confidence >= 0.5):
                logger.info("ollama_ingen_selector", watch_id=str(watch.id),
                            selector=advice.price_selector, confidence=advice.confidence,
                            page_type=advice.page_type, requires_js=advice.requires_js)

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

    async def _try_cpu_fallback(
        self,
        watch: Watch,
        scrape_result,
        parse_result,
    ) -> bool:
        """CPU-baseret fallback — ren Python/regex, ingen AI.

        Bruges når Ollama er offline eller slået fra.
        Scanner HTML'en lokalt med flere strategier for at finde priser.
        Returnerer True ved succes, False ved fejl.
        """
        from app.scraper.parsers.cpu_price_parser import CpuPriceParser

        if not scrape_result.html_snippet:
            logger.debug("cpu_fallback_ingen_html", watch_id=str(watch.id))
            return False

        try:
            cpu_result = CpuPriceParser.parse(
                content=scrape_result.html_snippet,
                url=watch.url,
            )
            if cpu_result and cpu_result.price:
                logger.info(
                    "cpu_fallback_pris",
                    watch_id=str(watch.id),
                    price=cpu_result.price,
                    parser=cpu_result.parser_used,
                    extractors=cpu_result.extractors_tried,
                )
                # Indpak i ParseResult-lignende objekt
                from types import SimpleNamespace
                cpu_parse = SimpleNamespace(
                    success=True,
                    price=cpu_result.price,
                    currency=cpu_result.currency or "DKK",
                    title=cpu_result.title,
                    stock_status=cpu_result.stock_status,
                    image_url=cpu_result.image_url,
                    parser_used=cpu_result.parser_used,
                    extractors_tried=cpu_result.extractors_tried or [],
                )
                await self.price_service.process_scraped_data(watch, cpu_parse, scrape_result.diagnostic)
                await self.db.commit()
                return True
            else:
                logger.debug("cpu_fallback_ingen_pris", watch_id=str(watch.id))
        except Exception as exc:
            logger.warning("cpu_fallback_fejl", watch_id=str(watch.id), error=str(exc))

        # CPU-fallback fejlede — returner False (original fejl håndteres udenfor)
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
