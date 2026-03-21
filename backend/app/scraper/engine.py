from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import structlog

from app.config import settings
from app.models.watch import Watch
from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import InlineJsonParser
from app.scraper.parsers.json_ld_parser import JsonLdParser
from app.scraper.parsers.shops.compumail import CompumailParser
from app.scraper.parsers.shops.computersalg import (
    ComputersalgParser,
    ELsalgParser,
    HappiiParser,
    KomplettParser,
)
from app.scraper.parsers.shops.biltema import BiltemaParser
from app.scraper.parsers.shops.elgigant import ElgigantParser
from app.scraper.parsers.shops.proshop import ProshopParser
from app.scraper.parsers.shops.woocommerce import WooCommerceParser
from app.scraper.providers.base import (
    ErrorType,
    FetchOptions,
    FetchProvider,
    FetchResult,
    ParseResult,
    PriceParser,
)
from app.scraper.providers.http_provider import HttpProvider
from app.scraper.providers.playwright_provider import PlaywrightProvider

logger = structlog.get_logger()

# Registry: domain → parser
SHOP_PARSERS: dict[str, PriceParser] = {
    "biltema.dk": BiltemaParser(),
    "www.biltema.dk": BiltemaParser(),
    "compumail.dk": CompumailParser(),
    "www.compumail.dk": CompumailParser(),
    "computersalg.dk": ComputersalgParser(),
    "www.computersalg.dk": ComputersalgParser(),
    "elgiganten.dk": ElgigantParser(),
    "www.elgiganten.dk": ElgigantParser(),
    "elsalg.dk": ELsalgParser(),
    "www.elsalg.dk": ELsalgParser(),
    "happii.dk": HappiiParser(),
    "www.happii.dk": HappiiParser(),
    "hmwtrading.dk": WooCommerceParser(),
    "www.hmwtrading.dk": WooCommerceParser(),
    "kaffelars.dk": WooCommerceParser(),
    "www.kaffelars.dk": WooCommerceParser(),
    "tingoggoejl.kronborgs.dk": WooCommerceParser(),
    "komplett.dk": KomplettParser(),
    "www.komplett.dk": KomplettParser(),
    "proshop.dk": ProshopParser(),
    "www.proshop.dk": ProshopParser(),
}

# Shops der kræver Playwright (aktiv bot-beskyttelse / JS-renderet pris)
PLAYWRIGHT_REQUIRED_DOMAINS = {
    "proshop.dk", "www.proshop.dk",
    "komplett.dk", "www.komplett.dk",
}

# Prissammenligningssider — returnér fejl med det samme, ingen HTTP-hentning
COMPARISON_SITES: set[str] = {
    "pricerunner.dk", "www.pricerunner.dk",
    "pricerunner.com", "www.pricerunner.com",
    "pricespy.dk", "www.pricespy.dk",
    "prisjakt.nu", "www.prisjakt.nu",
    "myketpris.dk", "www.myketpris.dk",
    "avxperten.dk", "pricespy.com",
}

# Signaler i HTML som indikerer bot-beskyttelse / challenge-siden
_CHALLENGE_SIGNALS = [
    "cf-browser-verification",
    "cf_chl_opt",
    "challenges.cloudflare.com",
    "__cf_chl_f_tk",
    "checking your browser",
    "verifying you are human",
    "ddos-guard",
    "_pxCaptcha",
    "px-captcha",
    "g-recaptcha",
    "h-captcha",
]

# Signaler der tyder på JavaScript-krævet rendering (minimal shell, intet indhold)
_JS_RENDER_SIGNALS = [
    '<div id="app"></div>',
    '<div id="root"></div>',
    '<div id="__nuxt"></div>',
    'ng-app=',
]

# Menneskevenlige fejlbeskeder pr. ErrorType
_ERROR_LABELS: dict[ErrorType, tuple[str, str]] = {
    ErrorType.parser_mismatch: (
        "Parser fandt ingen pris",
        "Konfigurér CSS-selectors manuelt, eller prøv JavaScript-rendering",
    ),
    ErrorType.js_render_required: (
        "Siden kræver JavaScript-rendering",
        "Aktivér Playwright-provider i watch-indstillinger",
    ),
    ErrorType.bot_protection: (
        "Siden blokerer automatisk hentning",
        "Siden anvender anti-bot-beskyttelse — kan ikke scrapes automatisk",
    ),
    ErrorType.transport_error: (
        "Netværksfejl",
        "Genprøver automatisk ved næste tjek",
    ),
    ErrorType.timeout: (
        "Siden svarer for langsomt",
        "Overvej at øge timeout i scraper-konfigurationen",
    ),
    ErrorType.comparison_site: (
        "Prissammenligningsside",
        "Tilføj en direkte produktside fra en butik i stedet",
    ),
    ErrorType.http_error: (
        "HTTP-fejl",
        "Tjek om URL stadig er tilgængelig",
    ),
}

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


def _classify_fetch_failure(fetch_result: FetchResult) -> ErrorType:
    """Map a failed FetchResult to an ErrorType (for cases not already set by provider)."""
    if fetch_result.error_type:
        return fetch_result.error_type
    if fetch_result.status_code in (403, 429):
        return ErrorType.bot_protection
    if fetch_result.status_code >= 400:
        return ErrorType.http_error
    return ErrorType.transport_error


def _classify_parse_failure(fetch_result: FetchResult) -> ErrorType:
    """Classify why parsing failed on a 200-OK page."""
    content = fetch_result.content
    content_lower = content.lower()

    # Challenge / bot protection page
    if any(sig in content_lower for sig in _CHALLENGE_SIGNALS):
        return ErrorType.bot_protection

    # Thin page that looks like a JavaScript SPA shell
    if fetch_result.html_length < 6_000 and any(sig in content for sig in _JS_RENDER_SIGNALS):
        return ErrorType.js_render_required

    return ErrorType.parser_mismatch


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
        diagnostic: dict | None = None,
        html_snippet: str | None = None,
    ) -> None:
        self.success = success
        self.price = price
        self.title = title
        self.stock_status = stock_status
        self.parser_used = parser_used
        self.error = error
        self.fetch_ok = fetch_ok
        self.status_code = status_code
        self.diagnostic = diagnostic
        self.html_snippet = html_snippet


def _build_diagnostic(
    fetch_result: FetchResult | None,
    parse_result: ParseResult | None,
    error_type: ErrorType | None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    fetch_info: dict = {
        "status_code": fetch_result.status_code if fetch_result else 0,
        "provider": fetch_result.provider if fetch_result else "unknown",
        "response_time_ms": round(fetch_result.response_time_ms, 1) if fetch_result else 0,
        "html_length": fetch_result.html_length if fetch_result else 0,
        "final_url": fetch_result.final_url if fetch_result else None,
    }

    parse_info: dict = {
        "extractors_tried": parse_result.extractors_tried if parse_result else [],
        "parser_used": parse_result.parser_used if parse_result else None,
        "price_found": parse_result.price if parse_result else None,
    }

    recommended_action = None
    if error_type and error_type in _ERROR_LABELS:
        recommended_action = _ERROR_LABELS[error_type][1]

    return {
        "checked_at": now,
        "fetch": fetch_info,
        "parse": parse_info,
        "error_type": error_type.value if error_type else None,
        "recommended_action": recommended_action,
    }


class ScraperEngine:
    """
    Orchestrerer provider + parser-pipeline for én Watch.

    Pipeline:
    1. Blokér prissammenligningssider
    2. Vælg provider (http / playwright)
    3. Fetch HTML med rate limiting og retry / HTTP/1.1-fallback
    4. Prøv parsers i prioriteret rækkefølge:
       a) JSON-LD (universelt)
       b) Shop-specifik parser
       c) User-konfigurerede CSS selectors
    5. Klassificér fejl og byg diagnostik
    6. Returnér ScrapeResult + ParseResult
    """

    async def scrape(self, watch: Watch) -> tuple[ScrapeResult, ParseResult | None]:
        domain = urlparse(watch.url).netloc.lower()

        # 1. Blokér prissammenligningssider øjeblikkeligt
        if domain in COMPARISON_SITES:
            label, action = _ERROR_LABELS[ErrorType.comparison_site]
            diag = _build_diagnostic(None, None, ErrorType.comparison_site)
            return ScrapeResult(
                success=False,
                error=f"{label} — {action}",
                fetch_ok=False,
                diagnostic=diag,
            ), None

        # 2. Afgør provider
        provider = self._resolve_provider(watch, domain)
        fetch_options = self._resolve_fetch_options(watch, domain)

        async with _get_semaphore():
            fetch_result = await provider.fetch(watch.url, fetch_options)

        if not fetch_result.ok:
            error_type = _classify_fetch_failure(fetch_result)
            diag = _build_diagnostic(fetch_result, None, error_type)
            return ScrapeResult(
                success=False,
                error=fetch_result.error or f"HTTP {fetch_result.status_code}",
                fetch_ok=False,
                status_code=fetch_result.status_code,
                diagnostic=diag,
            ), None

        # 3. Prøv parsers i rækkefølge, med sporing af forsøg
        parse_result = self._parse_with_fallback(fetch_result.content, watch, domain)

        if not parse_result.success:
            error_type = parse_result.error_type or _classify_parse_failure(fetch_result)
            parse_result.error_type = error_type
            if not parse_result.recommended_action and error_type in _ERROR_LABELS:
                parse_result.recommended_action = _ERROR_LABELS[error_type][1]
            diag = _build_diagnostic(fetch_result, parse_result, error_type)
            return ScrapeResult(
                success=False,
                error=parse_result.error or "Alle parsers fejlede",
                fetch_ok=True,
                status_code=fetch_result.status_code,
                diagnostic=diag,
                html_snippet=fetch_result.content[:12_000],
            ), parse_result

        diag = _build_diagnostic(fetch_result, parse_result, None)
        return ScrapeResult(
            success=True,
            price=parse_result.price,
            title=parse_result.title,
            stock_status=parse_result.stock_status,
            parser_used=parse_result.parser_used,
            diagnostic=diag,
        ), parse_result

    async def detect(self, url: str) -> ParseResult:
        """Kør scrape på en URL uden at gemme — til 'Tilføj watch' preview."""
        domain = urlparse(url).netloc.lower()

        if domain in COMPARISON_SITES:
            label, action = _ERROR_LABELS[ErrorType.comparison_site]
            return ParseResult(
                error=f"{label} — {action}",
                error_type=ErrorType.comparison_site,
                recommended_action=action,
            )

        needs_playwright = domain in PLAYWRIGHT_REQUIRED_DOMAINS
        provider: FetchProvider
        if needs_playwright and settings.playwright_enabled:
            provider = _get_playwright_provider()
        else:
            provider = _http_provider

        fetch_result = await provider.fetch(url)
        if not fetch_result.ok:
            return ParseResult(error=fetch_result.error or f"HTTP {fetch_result.status_code}")

        from types import SimpleNamespace
        fake_watch = SimpleNamespace(scraper_config=None, shop=None, url=url)
        return self._parse_with_fallback(fetch_result.content, fake_watch, domain)

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

        # 1. JSON-LD (mest pålidelig — schema.org Product)
        parsers.append(JsonLdParser())

        # 2. Shop-specifik parser (domain-specifik HTML-viden)
        shop_parser = SHOP_PARSERS.get(domain)
        if shop_parser:
            parsers.append(shop_parser)

        # 3. Inline JSON fallback (__NEXT_DATA__, x-magento-init, dataLayer)
        #    Dækker Next.js-shops og Magento 2 som shop-parseren måske mister
        parsers.append(InlineJsonParser())

        # 4. User-konfigurerede CSS selectors
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
        extractors_tried: list[str] = []

        for parser in parsers:
            extractors_tried.append(parser.parser_name)
            try:
                result = parser.parse(content, url)
                result.extractors_tried = extractors_tried[:]
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
            extractors_tried=extractors_tried,
        )


# Singleton engine
scraper_engine = ScraperEngine()
