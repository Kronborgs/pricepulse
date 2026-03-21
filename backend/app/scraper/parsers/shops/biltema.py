from __future__ import annotations

import json

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price, _deep_find
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()


class BiltemaParser(PriceParser):
    """
    Parser til biltema.dk.

    Biltema bruger et Next.js/React-frontend.
    Strategi 1: __NEXT_DATA__ → dehydratedState.queries → product price
    Strategi 2: window.__INITIAL_STATE__ JSON blob
    Strategi 3: JSON-LD priceSpecification (Biltema eksponerer schema.org)
    Strategi 4: CSS-selectors som fallback
    """

    parser_name = "biltema"

    _css_primary = CssSelectorParser(
        SelectorConfig(
            price_selector=(
                "[class*='price__Price'], "
                "[class*='Price__price'], "
                "[class*='product-price'], "
                "[data-price], "
                "[class*='ProductPrice'], "
                "span[class*='price']"
            ),
            title_selector="h1[class*='ProductName'], h1[class*='product'], h1",
            stock_selector=(
                "[class*='StockStatus'], "
                "[class*='stock-status'], "
                "[class*='availability'], "
                "[class*='Availability']"
            ),
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        # Strategi 1: __NEXT_DATA__ med dehydratedState (Biltema standard)
        result = self._try_next_data(soup)
        if result and result.success:
            return result

        # Strategi 2: CSS selector fallback
        result = self._css_primary.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
            return result

        return ParseResult(
            error="biltema: ingen pris fundet",
            parser_used=self.parser_name,
        )

    def _try_next_data(self, soup: BeautifulSoup) -> ParseResult | None:
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            return None
        try:
            data = json.loads(tag.get_text())
        except (json.JSONDecodeError, ValueError):
            return None

        # Søg bredt i hele __NEXT_DATA__ strukturen
        price_keys = frozenset({
            "price", "currentprice", "sellingprice", "saleprice",
            "finalprice", "grossprice", "priceamount", "pricevalue",
            "incvat", "inclvat", "retailprice", "listprice",
            "salespriceincvat", "displayprice", "priceincvat",
            "currentpriceincvat", "priceexvat", "netprice",
        })
        stock_keys = frozenset({"availability", "instock", "isinstock", "isavailable", "stock"})

        prices = _deep_find(data, price_keys, max_depth=12)
        clean_prices = [_clean_price(p) for p in prices if _clean_price(p) is not None and _clean_price(p) > 1]

        if not clean_prices:
            return None

        # Brug den laveste rimelige pris (undgå prishistorik-outliers)
        price = min(clean_prices)

        stocks = _deep_find(data, stock_keys, max_depth=12)
        stock_status = None
        for s in stocks:
            from app.scraper.parsers.inline_json_parser import _normalize_stock
            ns = _normalize_stock(s)
            if ns:
                stock_status = ns
                break

        # Hent titel
        title_keys = frozenset({"name", "title", "productname"})
        titles = _deep_find(data, title_keys, max_depth=6)
        title = next((str(t) for t in titles if isinstance(t, str) and 3 < len(t) < 200), None)

        return ParseResult(
            price=price,
            currency="DKK",
            stock_status=stock_status,
            title=title,
            parser_used=self.parser_name,
        )
