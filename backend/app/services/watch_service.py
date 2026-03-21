from __future__ import annotations

import uuid
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

        scrape_result, parse_result = await scraper_engine.scrape(watch)

        if scrape_result.success and parse_result:
            await self.price_service.process_scraped_data(watch, parse_result, scrape_result.diagnostic)
        else:
            await self.price_service.handle_scrape_error(
                watch,
                error=scrape_result.error or "Ukendt fejl",
                status_code=scrape_result.status_code,
                diagnostic=scrape_result.diagnostic,
            )

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
        """Find eksisterende shop baseret på domain."""
        domain = urlparse(url).netloc.lower()
        # Fjern www-præfix ved opslag
        base_domain = domain.removeprefix("www.")

        stmt = select(Shop).where(
            Shop.domain.in_([domain, base_domain, f"www.{base_domain}"])
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
