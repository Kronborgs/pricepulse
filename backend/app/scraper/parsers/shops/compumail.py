from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price
from app.scraper.providers.base import ParseResult, PriceParser


class CompumailParser(PriceParser):
    """
    Parser til compumail.dk.

    Compumail bruger en custom PHP shop. Strategier:
    1. data-price attribut på price-elementer  (primær: incl-moms)
    2. [itemprop='price'] microdata
    3. .price, .product-price, #price textContent
    4. Tekst-scan efter "XX.XXX kr" / "XX.XXX,-" mønster nær buy-button
    """

    parser_name = "compumail"

    # Strategi 1: Primær CSS — data-price attribut
    _css_primary = CssSelectorParser(
        SelectorConfig(
            price_selector="span.price[data-price]",
            title_selector="h1[itemprop='name']",
            stock_selector=None,
            image_selector=".product-lightbox-item.active img, .product-lightbox-item img",
            price_attr="data-price",
            stock_in_text="in stock",
            stock_out_text="out of stock",
        )
    )

    # Strategi 2: Enhver [data-price]
    _css_any_data_price = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-price]",
            price_attr="data-price",
            title_selector="h1[itemprop='name'], h1",
        )
    )

    # Strategi 3: Microdata
    _css_microdata = CssSelectorParser(
        SelectorConfig(
            price_selector="[itemprop='price']",
            price_attr="content",
            title_selector="h1[itemprop='name'], h1",
        )
    )

    # Strategi 4: Bred pris-tekst selector (class*='price' at product-section)
    _css_broad = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                ".product-price, "
                "#price, "
                ".price-now, "
                ".price-incl-vat, "
                "[class*='product'] [class*='price'], "
                "[class*='price'][class*='current'], "
                "[class*='price'][class*='final']"
            ),
            title_selector="h1[itemprop='name'], h1",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        for strategy in (
            self._css_primary,
            self._css_any_data_price,
            self._css_microdata,
            self._css_broad,
        ):
            result = strategy.parse(content, url)
            if result.success:
                result.parser_used = self.parser_name
                return result

        # Strategi 5: Tekst-scan — find pris i side-tekst vha. regex
        result = self._text_scan(content)
        if result and result.success:
            return result

        return ParseResult(
            error="compumail: ingen pris fundet",
            parser_used=self.parser_name,
        )

    # Kompakt mønster: "1.299 kr", "1299,-", "1.299,00", "1299.00 DKK"
    _PRICE_RE = re.compile(
        r"\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:kr\.?|-|DKK)\b",
        re.IGNORECASE,
    )

    def _text_scan(self, html: str) -> ParseResult | None:
        """
        Regressive fallback: scan synlig tekst for det første prisnummer
        nær et "Køb"-element el. lign.
        """
        soup = BeautifulSoup(html, "lxml")
        # Prioritér tekst nær buy-knapper
        for buy in soup.find_all(string=re.compile(r"Køb|Add to cart|buy", re.I))[:5]:
            parent = buy.parent
            for _ in range(4):
                if parent is None:
                    break
                m = self._PRICE_RE.search(parent.get_text(" ", strip=True))
                if m:
                    price = _clean_price(m.group(1))
                    if price and price > 1:
                        return ParseResult(
                            price=price,
                            currency="DKK",
                            parser_used=self.parser_name,
                        )
                parent = parent.parent
        return None

