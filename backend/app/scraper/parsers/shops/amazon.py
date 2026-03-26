from __future__ import annotations

import re

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()

# Regex til pris-tal fra a-offscreen spans (f.eks. "DKK1,036.38" eller "782,91")
_PRICE_RE = re.compile(r"[\d,\.]+")


class AmazonParser(PriceParser):
    """
    Parser til amazon.com, amazon.de, amazon.co.uk m.fl.

    Kræver Playwright — buy-box prisen populeres via JavaScript.

    Strategier:
    1. CSS: span.a-price.priceToPay .a-offscreen (renderet buy-box)
    2. CSS: #corePrice_feature_div .a-offscreen (alternativ buy-box)
    3. CSS: #price_inside_buybox (simpel buy-knap pris)
    4. CSS: .apexPriceToPay .a-offscreen (prime/apex pris)
    5. Generisk CSS-fallback
    """

    parser_name = "amazon"

    _css_primary = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                "span.a-price.priceToPay .a-offscreen, "
                ".apexPriceToPay .a-offscreen, "
                "#corePrice_feature_div .a-offscreen, "
                "#price_inside_buybox, "
                "#kindle-price, "
                "#buyNewSection .a-color-price"
            ),
            title_selector="#productTitle",
            stock_selector="#availability span, #availability",
            image_selector="#landingImage, #imgTagWrappingDiv img",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        # Strategi 1-4: CSS-baserede selectors (fungerer efter Playwright-rendering)
        result = self._css_primary.parse(content, url)
        if result.success and result.price and result.price > 1:
            result.parser_used = self.parser_name
            logger.debug("amazon: pris fundet via CSS", price=result.price, url=url)
            return result

        # Strategi 5: Manuel scan af a-offscreen spans — tag den første pris > 1
        price = self._scan_offscreen_spans(soup)
        if price and price > 1:
            title_tag = soup.select_one("#productTitle")
            stock_tag = soup.select_one("#availability span, #availability")
            img_tag = soup.select_one("#landingImage")
            return ParseResult(
                price=price,
                currency="DKK",
                title=title_tag.get_text(strip=True) if title_tag else None,
                stock_status=stock_tag.get_text(strip=True) if stock_tag else None,
                image_url=img_tag.get("src") if img_tag else None,
                parser_used=self.parser_name,
            )

        return ParseResult(
            error="amazon: ingen buy-box pris fundet (er Playwright aktiv?)",
            parser_used=self.parser_name,
        )

    def _scan_offscreen_spans(self, soup: BeautifulSoup) -> float | None:
        """
        Scan alle .a-offscreen spans og returnér den første valid pris > 1.
        Springer over priser fra variations-sektionen (andre varianter).
        """
        # Prioritér buy-box containere frem for hele siden
        containers = soup.select(
            "#buybox, #centerCol, #apex_desktop, #corePriceDisplay_desktop_feature_div"
        )
        search_root = containers[0] if containers else soup

        for span in search_root.select(".a-offscreen"):
            raw = span.get_text(strip=True)
            price = _clean_price(raw)
            if price and price > 1:
                return price
        return None
