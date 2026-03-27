from __future__ import annotations

import re

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()

# ASIN fra URL: /dp/B0BVTSVQVQ eller /gp/product/B0BVTSVQVQ
_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")


class AmazonParser(PriceParser):
    """
    Parser til amazon.com, amazon.de, amazon.co.uk m.fl.

    Strategier:
    0. Twister-data JSON (statisk HTML) — "defaultAsin":"<ASIN>"...priceWithoutCurrencySymbol
       Fungerer uden Playwright. Amazon gemmer alle variant-priser her.
    1. CSS: span.a-price.priceToPay .a-offscreen (kun ved Playwright-rendering)
    2. CSS-fallback: øvrige buy-box selectors
    """

    parser_name = "amazon"

    _css_primary = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                "span.a-price.priceToPay .a-offscreen, "
                ".apexPriceToPay .a-offscreen, "
                "#corePrice_feature_div .a-offscreen, "
                "#price_inside_buybox, "
                "#kindle-price"
            ),
            title_selector="#productTitle",
            stock_selector="#availability span, #availability",
            image_selector="#landingImage, #imgTagWrappingDiv img",
            stock_in_text="in stock",
            stock_out_text="out of stock",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        # Strategi 0: Twister-data — priser i statisk HTML, ingen Playwright nødvendig
        result = self._try_twister_data(content, url, soup)
        if result:
            return result

        # Strategi 1-2: CSS (virker kun efter Playwright-rendering)
        result = self._css_primary.parse(content, url)
        if result.success and result.price and result.price > 1:
            result.parser_used = self.parser_name
            logger.debug("amazon: pris fundet via CSS (Playwright)", price=result.price, url=url)
            return result

        # Strategi 3: Manuel scan af a-offscreen i buy-box containere
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
            error="amazon: ingen pris fundet i twister-data eller buy-box",
            parser_used=self.parser_name,
        )

    def _try_twister_data(self, content: str, url: str, soup: BeautifulSoup) -> ParseResult | None:
        """
        Amazon gemmer variant-priser i twister_feature_div JSON-blokken i statisk HTML.

        Format:
        {"defaultAsin":"B0BVTSVQVQ","dimensionValueState":"SELECTED",
         "slots":[{"displayData":{"priceWithoutCurrencySymbol":"589.415022",...}}]}

        Vi finder ASIN fra URL, søger derefter priceWithoutCurrencySymbol
        inden for de næste ~1000 tegn efter defaultAsin-markøren.

        Returnerer også alle variant-priser som metadata (til fremtidig brug).
        """
        asin_match = _ASIN_RE.search(url)
        if not asin_match:
            return None
        asin = asin_match.group(1)

        # Find den specifikke variant-blok for dette ASIN
        marker_pat = rf'"defaultAsin"\s*:\s*"{re.escape(asin)}"'
        marker = re.search(marker_pat, content)
        if not marker:
            logger.debug("amazon: defaultAsin ikke fundet i twister-data", asin=asin, url=url)
            return None

        # Søg priceWithoutCurrencySymbol inden for 1000 tegn fremad fra markøren
        window = content[marker.start(): marker.start() + 1000]
        price_match = re.search(r'"priceWithoutCurrencySymbol"\s*:\s*"([0-9]+\.[0-9]+)"', window)
        if not price_match:
            logger.debug("amazon: priceWithoutCurrencySymbol ikke fundet for ASIN", asin=asin)
            return None

        price = _clean_price(price_match.group(1))
        if not price or price <= 1:
            return None

        # Titel og billede fra statisk HTML (er til stede uden Playwright)
        title_tag = soup.select_one("#productTitle")
        img_tag = soup.select_one("#landingImage, #imgTagWrappingDiv img")

        # Optionelt: saml alle variant-priser (til log/debug)
        variants: dict[str, float] = {}
        for m_asin, m_price_str in re.findall(
            r'"defaultAsin"\s*:\s*"([A-Z0-9]{10})"[^}]{0,800}?"priceWithoutCurrencySymbol"\s*:\s*"([0-9]+\.[0-9]+)"',
            content,
        ):
            p = _clean_price(m_price_str)
            if p and p > 1:
                variants[m_asin] = p
        if variants:
            logger.debug("amazon: variant-priser fundet", variants=variants, watching=asin, url=url)

        logger.info("amazon: twister-data pris fundet", asin=asin, price=price, url=url)
        return ParseResult(
            price=price,
            currency="DKK",
            title=title_tag.get_text(strip=True) if title_tag else None,
            image_url=img_tag.get("src") if img_tag else None,
            parser_used=self.parser_name,
        )

    def _scan_offscreen_spans(self, soup: BeautifulSoup) -> float | None:
        """Scan .a-offscreen spans i buy-box containere — fallback til Playwright."""
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

