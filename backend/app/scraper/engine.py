from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import structlog

from app.config import settings
from app.models.watch import Watch
from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.json_ld_parser import JsonLdParser
from app.scraper.parsers.shops.compumail import CompumailParser
from app.scraper.parsers.shops.computersalg import (
    ComputersalgParser,
    ELsalgParser,
    HappiiParser,
    KomplettParser,
)
from app.scraper.parsers.shops.proshop import ProshopParser
from app.scraper.providers.base import FetchOptions, FetchProvider, ParseResult, PriceParser
from app.scraper.providers.http_provider import HttpProvider
from app.scraper.providers.playwright_provider import PlaywrightProvider

logger = structlog.get_logger()

# Registry: domain → parser
SHOP_PARSERS: dict[str, PriceParser] = {
    "compumail.dk": CompumailParser(),
    "www.compumail.dk": CompumailParser(),
    "computersalg.dk": ComputersalgParser(),
    "www.computersalg.dk": ComputersalgParser(),
    "elsalg.dk": ELsalgParser(),
    "www.elsalg.dk": ELsalgParser(),
    "happii.dk": HappiiParser(),
    "www.happii.dk": HappiiParser(),
    "komplett.dk": KomplettParser(),
    "www.komplett.dk": KomplettParser(),
    "proshop.dk": ProshopParser(),
    "www.proshop.dk": ProshopParser(),
}

# Shops der altid kræver Playwright
PLAYWRIGHT_REQUIRED_DOMAINS = {"proshop.dk", "www.proshop.dk"}

# Singleton providers
_http_provider = HttpProvider()
_playwright_provider: PlaywrightProvider | None = None
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.scraper_max_concurrent)
    return _semaphore


def _get_playwright_provider() -> PlaywrightProvider:
    global _playwright_provider
    if _playwright_provider is None:
        _playwright_provider = PlaywrightProvider()
    return _playwright_provider


class ScrapeResult:
    def __init__(
        self,
        success: bool,
        price: float | None = None,
        title: str | None = None,
        stock_status: str | None = None,
        parser_used: str = "",
        error: str | None = None,
        fetch_ok: bool = True,
        status_code: int = 0,
    ) -> None:
        self.success = success
        self.price = price
        self.title = title
        self.stock_status = stock_status
        self.parser_used = parser_used
        self.error = error
        self.fetch_ok = fetch_ok
        self.status_code = status_code


class ScraperEngine:
    """
    Orchestrerer provider + parser-pipeline for én Watch.

    Pipeline:
    1. Vælg provider (http / playwright)
    2. Fetch HTML med rate limiting og retry
    3. Prøv parsers i prioriteret rækkefølge:
       a) JSON-LD (universelt)
       b) Shop-specifik parser
       c) User-konfigurerede CSS selectors
    4. Returnér ScrapeResult
    """

    async def scrape(self, watch: Watch) -> tuple[ScrapeResult, ParseResult | None]:
        domain = urlparse(watch.url).netloc.lower()

        # Afgør provider
        provider = self._resolve_provider(watch, domain)
        fetch_options = self._resolve_fetch_options(watch, domain)

        async with _get_semaphore():
            fetch_result = await provider.fetch(watch.url, fetch_options)

        if not fetch_result.ok:
            scrape_result = ScrapeResult(
                success=False,
                error=fetch_result.error or f"HTTP {fetch_result.status_code}",
                fetch_ok=False,
                status_code=fetch_result.status_code,
            )
            return scrape_result, None

        # Prøv parsers i rækkefølge
        parse_result = self._parse_with_fallback(fetch_result.content, watch, domain)

        if not parse_result.success:
            return ScrapeResult(
                success=False,
                error=parse_result.error or "Alle parsers fejlede",
                fetch_ok=True,
            ), parse_result

        return ScrapeResult(
            success=True,
            price=parse_result.price,
            title=parse_result.title,
            stock_status=parse_result.stock_status,
            parser_used=parse_result.parser_used,
        ), parse_result

    async def detect(self, url: str) -> ParseResult:
        """Kør scrape på en URL uden at gemme — til 'Tilføj watch' preview."""
        domain = urlparse(url).netloc.lower()
        needs_playwright = domain in PLAYWRIGHT_REQUIRED_DOMAINS

        provider: FetchProvider
        if needs_playwright and settings.playwright_enabled:
            provider = _get_playwright_provider()
        else:
            provider = _http_provider

        fetch_result = await provider.fetch(url)
        if not fetch_result.ok:
            return ParseResult(error=fetch_result.error or f"HTTP {fetch_result.status_code}")

        # Byg en midlertidig watch-lignende objekt til parser-lookup
        class _FakeWatch:
            scraper_config = None
            shop = None

        return self._parse_with_fallback(fetch_result.content, _FakeWatch(), domain)

    def _resolve_provider(self, watch: Watch, domain: str) -> FetchProvider:
        explicit = watch.provider or "http"
        if explicit == "playwright" or domain in PLAYWRIGHT_REQUIRED_DOMAINS:
            if settings.playwright_enabled:
                return _get_playwright_provider()
            else:
                logger.warning(
                    "Playwright kræves men er ikke aktiveret — falder tilbage til HTTP",
                    domain=domain,
                )
        return _http_provider

    def _resolve_fetch_options(self, watch: Watch, domain: str) -> FetchOptions:
        cfg = watch.scraper_config or {}
        return FetchOptions(
            timeout=float(cfg.get("timeout", 30.0)),
            wait_for_selector=cfg.get("wait_for_selector"),
        )

    def _parse_with_fallback(
        self, content: str, watch: object, domain: str
    ) -> ParseResult:
        parsers: list[PriceParser] = []

        # 1. JSON-LD (mest pålidelig)
        parsers.append(JsonLdParser())

        # 2. Shop-specifik parser
        shop_parser = SHOP_PARSERS.get(domain)
        if shop_parser:
            parsers.append(shop_parser)

        # 3. User-konfigurerede CSS selectors
        cfg = getattr(watch, "scraper_config", None) or {}
        if cfg.get("price_selector"):
            parsers.append(
                CssSelectorParser(
                    SelectorConfig(
                        price_selector=cfg["price_selector"],
                        title_selector=cfg.get("title_selector"),
                        stock_selector=cfg.get("stock_selector"),
                        stock_in_text=cfg.get("stock_in_text", "på lager"),
                        stock_out_text=cfg.get("stock_out_text", "udsolgt"),
                    )
                )
            )

        url = getattr(watch, "url", "")
        for parser in parsers:
            try:
                result = parser.parse(content, url)
                if result.success:
                    logger.debug(
                        "Parser lykkedes",
                        parser=parser.parser_name,
                        price=result.price,
                        url=url,
                    )
                    return result
            except Exception as e:
                logger.warning(
                    "Parser kastede exception",
                    parser=parser.parser_name,
                    error=str(e),
                    url=url,
                )

        return ParseResult(
            error="Ingen parser lykkedes. Konfigurér CSS selectors manuelt.",
            parser_used="none",
        )


# Singleton engine
scraper_engine = ScraperEngine()
