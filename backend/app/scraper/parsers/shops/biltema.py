from __future__ import annotations

import json
import re

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
                # Biltema Next.js genererede klasser (CSS modules)
                "[class*='price__Price'], "
                "[class*='Price__price'], "
                "[class*='ProductPrice'], "
                "[class*='product-price'], "
                # data-attributter
                "[data-price], "
                "[data-product-price], "
                # microdata
                "[itemprop='price'], "
                # bred fallback
                "span[class*='price'], "
                "div[class*='price']"
            ),
            title_selector=(
                "h1[class*='ProductName'], "
                "h1[class*='product'], "
                "h1[class*='title'], "
                "[itemprop='name'], "
                "h1"
            ),
            stock_selector=(
                "[class*='StockStatus'], "
                "[class*='stock-status'], "
                "[class*='InStock'], "
                "[class*='availability'], "
                "[class*='Availability'], "
                "[class*='stock__'], "
                "[data-stock-status]"
            ),
            image_selector=(
                "[class*='ProductImage'] img, "
                "[class*='product-image'] img, "
                "[class*='Gallery'] img, "
                "meta[property='og:image']"
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

        # Strategi 2: window.__INITIAL_STATE__ (ikke-Next.js React-variant)
        result = self._try_initial_state(soup)
        if result and result.success:
            return result

        # Strategi 3: CSS selector fallback
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

        price_keys = frozenset({
            "price", "currentprice", "sellingprice", "saleprice",
            "finalprice", "grossprice", "priceamount", "pricevalue",
            "incvat", "inclvat", "retailprice", "listprice",
            "salespriceincvat", "displayprice", "priceincvat",
            "currentpriceincvat", "priceexvat", "netprice",
        })
        stock_keys = frozenset({"availability", "instock", "isinstock", "isavailable", "stock"})
        title_keys = frozenset({"name", "title", "productname"})
        image_keys = frozenset({"image", "imageurl", "thumbnail", "imageuri", "imagesrc"})

        page_props = data.get("props", {}).get("pageProps", {})

        # Søgescopes fra mest specifik til bredest:
        # 1. React Query dehydratedState (Biltema bruger Next.js + React Query)
        # 2. Direkte pageProps.product/item-nøgler
        # 3. Hele pageProps
        # 4. Bred fallback: hele __NEXT_DATA__
        search_scopes: list[dict] = []
        queries = page_props.get("dehydratedState", {}).get("queries", [])
        for q in queries[:5]:
            q_data = q.get("state", {}).get("data")
            if isinstance(q_data, dict):
                search_scopes.append(q_data)
        for key in ("product", "item", "initialProduct", "articleData", "productData"):
            obj = page_props.get(key)
            if isinstance(obj, dict):
                search_scopes.append(obj)
        if page_props:
            search_scopes.append(page_props)
        search_scopes.append(data)  # bred fallback

        result_price: float | None = None
        result_stock = None
        result_title: str | None = None
        result_image: str | None = None

        for scope in search_scopes:
            if result_price is None:
                raw_prices = _deep_find(scope, price_keys, max_depth=8)
                # Tag den FØRSTE gyldige pris i dette scope (DFS-rækkefølge = øverste/mest
                # relevante felt først).  Undgå kun at bruge min() som kan ramle ind i
                # billige tilbehørsvarer fra relaterede produkter.
                for rp in raw_prices:
                    cp = _clean_price(rp)
                    if cp is not None and cp > 1:
                        result_price = cp
                        break

            if result_stock is None:
                stocks = _deep_find(scope, stock_keys, max_depth=8)
                for s in stocks:
                    from app.scraper.parsers.inline_json_parser import _normalize_stock
                    ns = _normalize_stock(s)
                    if ns:
                        result_stock = ns
                        break

            if result_title is None:
                titles = _deep_find(scope, title_keys, max_depth=6)
                result_title = next(
                    (str(t) for t in titles if isinstance(t, str) and 3 < len(t) < 200),
                    None,
                )

            if result_image is None:
                images = _deep_find(scope, image_keys, max_depth=8)
                result_image = next(
                    (str(i) for i in images if isinstance(i, str) and i.startswith("http")),
                    None,
                )

            # Har vi pris og titel fra dette scope — stop her, gå ikke bredere
            if result_price is not None and result_title is not None:
                break

        if result_price is None:
            return None

        if not result_image:
            og = soup.find("meta", property="og:image")
            if og:
                result_image = og.get("content")

        return ParseResult(
            price=result_price,
            currency="DKK",
            stock_status=result_stock,
            title=result_title,
            image_url=result_image,
            parser_used=self.parser_name,
        )

    def _try_initial_state(self, soup: BeautifulSoup) -> ParseResult | None:
        """Biltema React-app kan gemme data i window.__INITIAL_STATE__ i et inline script."""
        _decoder = json.JSONDecoder()
        price_keys = frozenset({
            "price", "currentprice", "sellingprice", "saleprice",
            "finalprice", "grossprice", "priceamount", "pricevalue",
            "incvat", "inclvat", "salespriceincvat", "displayprice",
            "priceincvat", "listprice", "retailprice",
        })
        for script in soup.find_all("script"):
            text = script.get_text()
            if "__INITIAL_STATE__" not in text:
                continue
            m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{)", text)
            if not m:
                continue
            try:
                data, _ = _decoder.raw_decode(text[m.start(1):])
            except (json.JSONDecodeError, ValueError):
                continue
            prices = _deep_find(data, price_keys, max_depth=12)
            price = next(
                (cp for p in prices for cp in [_clean_price(p)] if cp is not None and cp > 1),
                None,
            )
            if price is not None:
                return ParseResult(
                    price=price,
                    currency="DKK",
                    parser_used=self.parser_name,
                )
        return None
