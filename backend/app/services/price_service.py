from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_event import PriceEvent
from app.models.price_history import PriceHistory
from app.models.watch import Watch
from app.scraper.providers.base import ParseResult

logger = structlog.get_logger()

# Antal fejl i træk før watch sættes til "error"
ERROR_THRESHOLD = 5
# Antal fejl i træk (med HTTP 403/429) før watch sættes til "blocked"
BLOCK_THRESHOLD = 3


class PriceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_scraped_data(
        self, watch: Watch, parse_result: ParseResult, diagnostic: dict | None = None
    ) -> bool:
        """
        Behandl scrapede data:
        - Gem i price_history
        - Detektér ændringer
        - Opret deduplikerede price_events
        - Opdatér watch-status
        Returnerer True hvis der var en ændring.
        """
        now = datetime.now(timezone.utc)
        new_price = parse_result.price
        new_stock = parse_result.stock_status

        old_price = float(watch.current_price) if watch.current_price is not None else None
        old_stock = watch.current_stock_status

        price_changed = old_price is not None and new_price != old_price
        stock_changed = old_stock != new_stock
        is_initial = watch.last_checked_at is None

        # Altid gem et historikpunkt
        history = PriceHistory(
            watch_id=watch.id,
            price=new_price,
            currency=parse_result.currency or "DKK",
            stock_status=new_stock,
            recorded_at=now,
            is_change=price_changed or stock_changed,
            raw_data=parse_result.raw_data or {},
        )
        self.db.add(history)

        # Gem event ved initial check eller ændring
        if is_initial or price_changed or stock_changed:
            event_type = "initial" if is_initial else (
                "price_change" if price_changed else "stock_change"
            )
            delta = None
            delta_pct = None
            if price_changed and old_price and new_price:
                delta = round(new_price - old_price, 2)
                delta_pct = round((delta / old_price) * 100, 2)

            dedup_key = (
                f"{watch.id}:{event_type}:{old_price}:{new_price}:{old_stock}:{new_stock}"
            )

            # Atomisk INSERT ... ON CONFLICT DO NOTHING — sikker mod parallel scraping
            await self.db.execute(
                pg_insert(PriceEvent)
                .values(
                    id=uuid.uuid4(),
                    watch_id=watch.id,
                    event_type=event_type,
                    old_price=old_price,
                    new_price=new_price,
                    price_delta=delta,
                    price_delta_pct=delta_pct,
                    old_stock=old_stock,
                    new_stock=new_stock,
                    occurred_at=now,
                    dedup_key=dedup_key,
                    extra_data={"parser": parse_result.parser_used},
                )
                .on_conflict_do_nothing(index_elements=["dedup_key"])
            )

            if price_changed:
                logger.info(
                    "Prisændring detekteret",
                    watch_id=str(watch.id),
                    title=watch.title,
                    old_price=old_price,
                    new_price=new_price,
                    delta=delta,
                    delta_pct=delta_pct,
                )

        # Opdatér watch
        watch.current_price = new_price
        watch.current_stock_status = new_stock
        watch.last_checked_at = now
        watch.last_error = None
        watch.error_count = 0
        watch.status = "active"
        if diagnostic is not None:
            watch.last_diagnostic = diagnostic

        if price_changed or stock_changed:
            watch.last_changed_at = now

        # Sæt titel og billede hvis ikke allerede sat
        if parse_result.title and not watch.title:
            watch.title = parse_result.title
        if parse_result.image_url and not watch.image_url:
            watch.image_url = parse_result.image_url

        # Auto-link til Product baseret på titel (selvhelende)
        if watch.title and not watch.product_id:
            await self._auto_link_product(watch)

        await self.db.commit()
        return price_changed or stock_changed

    async def _auto_link_product(self, watch: Watch) -> None:
        """Find eller opret et Product baseret på watch-titlen og link det."""
        from app.models.product import Product

        stmt = select(Product).where(
            func.lower(Product.name) == watch.title.lower()
        )
        product = (await self.db.execute(stmt)).scalar_one_or_none()
        if not product:
            product = Product(name=watch.title, image_url=watch.image_url)
            self.db.add(product)
            await self.db.flush()
        watch.product_id = product.id

    async def handle_scrape_error(
        self, watch: Watch, error: str, status_code: int = 0, diagnostic: dict | None = None
    ) -> None:
        """Registrér fejl og opdatér watch-status."""
        now = datetime.now(timezone.utc)
        watch.last_checked_at = now
        watch.last_error = error
        watch.error_count = (watch.error_count or 0) + 1
        if diagnostic is not None:
            watch.last_diagnostic = diagnostic

        # Blocked: HTTP 403/429 over tærskel
        if status_code in (403, 429) and watch.error_count >= BLOCK_THRESHOLD:
            watch.status = "blocked"
            logger.warning(
                "Watch markeret som blokeret",
                watch_id=str(watch.id),
                url=watch.url,
                status_code=status_code,
            )
        elif watch.error_count >= ERROR_THRESHOLD:
            watch.status = "error"
            logger.error(
                "Watch markeret som fejl",
                watch_id=str(watch.id),
                url=watch.url,
                error=error,
                error_count=watch.error_count,
            )

        # Gem fejl-event
        dedup_key = f"{watch.id}:error:{now.strftime('%Y-%m-%d-%H')}"
        await self.db.execute(
            pg_insert(PriceEvent)
            .values(
                id=uuid.uuid4(),
                watch_id=watch.id,
                event_type="error",
                occurred_at=now,
                dedup_key=dedup_key,
                extra_data={"error": error, "status_code": status_code},
            )
            .on_conflict_do_nothing(index_elements=["dedup_key"])
        )

        await self.db.commit()
