from __future__ import annotations

import json
import re

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price, _deep_find, _normalize_stock
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()


class WooCommerceParser(PriceParser):
    """
    Generisk WooCommerce-parser.
    Dækker alle WooCommerce-butikker: hmwtrading.dk, kaffelars.dk, o.a.

    Strategier i rækkefølge:
    1. woocommerce_params / product_page JSON-blob
    2. CSS: .woocommerce-Price-amount bdi (standard WC priselementet)
    3. Schema.org JSON-LD (WC genererer det selv)
    4. Bred CSS fallback
    """

    parser_name = "woocommerce"

    # Strategi 2: Standard WooCommerce pris-markup + bredere platfomselectors
    # WC bruger <bdi> indeni .woocommerce-Price-amount.amount;
    # Dandomain bruger .productPrice, .product-price, [itemprop='price']
    _css_primary = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                ".woocommerce-Price-amount.amount bdi, "
                ".woocommerce-Price-amount.amount, "
                "p.price ins .woocommerce-Price-amount, "
                "p.price > .woocommerce-Price-amount, "
                "[itemprop='price'], "
                ".productPrice .price, "
                ".productPrice, "
                ".product-price .price, "
                ".product-price"
            ),
            title_selector=(
                ".product_title.entry-title, "
                "h1.entry-title, "
                "h1.product-title, "
                "h1"
            ),
            stock_selector=(
                ".woocommerce-product-details__short-description, "
                ".stock, "
                "p.stock, "
                "[class*='stock']"
            ),
            image_selector=".woocommerce-product-gallery__image img, .wp-post-image",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    # Strategi 4: Bredere CSS fallback
    _css_fallback = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                "[class*='woocommerce'] [class*='price'], "
                ".product-page [class*='price'], "
                ".entry-summary [class*='price'], "
                "[class*='productprice'], "
                "[class*='product-price'], "
                "[class*='buybox'] [class*='price'], "
                "[class*='pris']"
            ),
            title_selector="h1",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        # Strategi 1: wc_product_block_data eller woocommerce_params JSON blob
        result = self._try_wc_json(soup)
        if result and result.success:
            return result

        # Strategi 2: Standard WC CSS
        result = self._css_primary.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
            # Berig med lagerstatus via tekst-scan hvis mangler
            if result.stock_status is None:
                result.stock_status = self._scan_stock(soup)
            return result

        # Strategi 3: Bred fallback
        result = self._css_fallback.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
            return result

        return ParseResult(
            error="woocommerce: ingen pris fundet",
            parser_used=self.parser_name,
        )

    def _try_wc_json(self, soup: BeautifulSoup) -> ParseResult | None:
        """
        WooCommerce injicerer produktdata som JS-variable i <script>-tags.
        Søg efter varianter, addToCart-data, eller wpb_wc data.
        """
        price_re = re.compile(
            r'"(?:price|regular_price|sale_price)"\s*:\s*"?([\d.,]+)"?',
            re.IGNORECASE,
        )
        for script in soup.find_all("script"):
            text = script.get_text()
            if "woocommerce" not in text.lower() and "add_to_cart" not in text.lower():
                continue
            m = price_re.search(text)
            if m:
                price = _clean_price(m.group(1))
                if price:
                    return ParseResult(
                        price=price,
                        currency="DKK",
                        parser_used=self.parser_name,
                    )
        return None

    def _scan_stock(self, soup: BeautifulSoup) -> str | None:
        for el in soup.find_all(string=lambda t: t and ("lager" in t.lower() or "udsolgt" in t.lower()))[:5]:
            t = el.strip().lower()
            if "på lager" in t or "in stock" in t:
                return "in_stock"
            if "ikke på lager" in t or "udsolgt" in t or "out of stock" in t:
                return "out_of_stock"
        return None
