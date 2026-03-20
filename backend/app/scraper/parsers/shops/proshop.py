from __future__ import annotations

import structlog

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import FetchOptions, ParseResult, PriceParser

logger = structlog.get_logger()


class ProshopParser(PriceParser):
    """
    Parser til proshop.dk.
    Proshop anvender Cloudflare-beskyttelse — HTTP provider vil typisk
    resultere i HTTP 403 eller en Cloudflare challenge-side.
    Dette er markeret og tydeligt rapporteret til brugeren.
    Provider: playwright (kræver PLAYWRIGHT_ENABLED=true).
    """

    parser_name = "proshop"
    REQUIRED_PROVIDER = "playwright"

    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=".site-currency-attention, .site-price .site-currency-attention",
            title_selector="h1.product-title",
            stock_selector=".stock-status",
            image_selector=".product-image-wrapper img",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        # Detekter Cloudflare challenge-side
        if "just a moment" in content.lower() or "cf-browser-verification" in content.lower():
            logger.warning(
                "Proshop: Cloudflare challenge detekteret — playwright kræves",
                url=url,
            )
            return ParseResult(
                error=(
                    "Siden er beskyttet af Cloudflare. "
                    "Aktiver Playwright-provider i watch-konfigurationen."
                ),
                parser_used=self.parser_name,
            )

        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result

    @property
    def fetch_options(self) -> FetchOptions:
        """Playwright-specifikke fetch-options til proshop."""
        return FetchOptions(
            timeout=45.0,
            wait_for_selector=".site-currency-attention",
            wait_for_networkidle=True,
        )
