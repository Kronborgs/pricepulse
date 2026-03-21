from __future__ import annotations

import json

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price, _deep_find, _normalize_stock
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()


class ElgigantParser(PriceParser):
    """
    Parser til www.elgiganten.dk (Elkjøp Nordic platform).

    Siden er en hybrid SSR/CSR Next.js-app. Prisen er tilgængelig i
    server-renderet HTML som en ``data-primary-price``-attribut på
    buy-box-elementet. Ingen __NEXT_DATA__ blob er indlejret, og JSON-LD
    bruger priceSpecification (ex-moms) frem for et direkte ``price``-felt.

    Strategi 1: specifik buy-box selector                      (mest præcis)
    Strategi 2: første [data-primary-price] på siden           (bredere fallback)
    """

    parser_name = "elgigant"

    # Strategi 1: Specifik buy-box — undgår tilbehørs-priser
    _strategy_buybox = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-cro='pdp-main-price-box'] [data-primary-price]",
            price_attr="data-primary-price",
            title_selector="h1",
            image_selector="img[data-nimg][alt][src*='dv_web']",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    # Strategi 2: Første data-primary-price-element på siden
    # (produkt-prisen optræder altid før tilbehørs-priser i DOM-rækkefølge)
    _strategy_any = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-primary-price]",
            price_attr="data-primary-price",
            title_selector="h1",
        )
    )

    # Strategi 3: microdata / schema.org content-attribut
    _strategy_microdata = CssSelectorParser(
        SelectorConfig(
            price_selector="[itemprop='price']",
            price_attr="content",
            title_selector="h1",
            # Stock: leveringsinformation-sektionen på elkjøp/elgiganten
            stock_selector=(
                "[data-testid='stock-status'], "
                "[class*='stock-status'], "
                "[class*='StockStatus'], "
                "[class*='delivery-status'], "
                ".elg-availability, "
                ".availability-status, "
                "[data-testid='add-to-cart-section'] [class*='stock'], "
                "[class*='pdp'] [class*='stock']"
            ),
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        # Strategi 0: __NEXT_DATA__ (Elgiganten bruger Next.js — pris i server-state)
        soup = BeautifulSoup(content, "lxml")
        result = self._try_next_data(soup)
        if result and result.success:
            return result

        for strategy in (self._strategy_buybox, self._strategy_any, self._strategy_microdata):
            result = strategy.parse(content, url)
            if result.success:
                result.parser_used = self.parser_name
                # Forsøg at berige med stock-status fra strategi 3 hvis mangler
                if result.stock_status is None:
                    stock_result = self._strategy_microdata.parse(content, url)
                    if stock_result.stock_status:
                        result.stock_status = stock_result.stock_status
                return result

        return ParseResult(
            error="elgigant: ingen pris fundet via data-primary-price eller microdata",
            parser_used=self.parser_name,
        )

    def _try_next_data(self, soup: BeautifulSoup) -> ParseResult | None:
        """Elgiganten (Elkjøp) bruger Next.js — produktdata i __NEXT_DATA__."""
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            return None
        try:
            data = json.loads(tag.get_text())
        except (json.JSONDecodeError, ValueError):
            return None

        price_keys = frozenset({
            "price", "currentprice", "saleprice", "sellingprice",
            "finalprice", "grossprice", "inclvat", "incvat", "listprice",
        })
        prices = _deep_find(data, price_keys, max_depth=12)
        clean = [p for p in (_clean_price(v) for v in prices) if p and p > 1]
        if not clean:
            return None

        price = min(clean)

        stock_keys = frozenset({"availability", "instock", "isinstock", "isavailable", "stockstatus"})
        stock_status = None
        for v in _deep_find(data, stock_keys, max_depth=12):
            s = _normalize_stock(v)
            if s:
                stock_status = s
                break

        title_keys = frozenset({"name", "title", "productname"})
        title = next(
            (str(t) for t in _deep_find(data, title_keys, max_depth=6)
             if isinstance(t, str) and 3 < len(t) < 200),
            None,
        )

        return ParseResult(
            price=price,
            currency="DKK",
            stock_status=stock_status,
            title=title,
            parser_used=self.parser_name,
        )
