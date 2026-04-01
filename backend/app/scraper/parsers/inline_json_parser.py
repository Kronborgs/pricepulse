from __future__ import annotations

import json
import re
from typing import Any

import structlog
from bs4 import BeautifulSoup

from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()


# ── Hjælpefunktioner ─────────────────────────────────────────────────────────

def _clean_price(v: Any) -> float | None:
    """Konvertér enhver pris-repræsentation til float."""
    if isinstance(v, (int, float)):
        return float(v) if v > 1 else None
    if isinstance(v, str):
        # Strip valutasymboler og koder
        for sym in ("€", "$", "£", "¥", "₩", "kr.", "kr", "DKK", "EUR", "USD", "GBP", "SEK", "NOK", "CHF", "CAD", "AUD", "JPY"):
            v = v.replace(sym, "")
        v = v.replace("\xa0", "").replace(" ", "").strip()
        # Dansk ,-  suffix = ingen decimaler (f.eks. "949,-" → "949")
        if v.endswith(",-"):
            v = v[:-2]
        elif "," in v and "." in v:
            last_comma = v.rfind(",")
            last_dot = v.rfind(".")
            if last_dot > last_comma:
                # US format: 1,036.38 → slet tusinde-separatoren
                v = v.replace(",", "")
            else:
                # EU format: 1.036,38 → slet tusind-pkt, erstat komma med pkt
                v = v.replace(".", "").replace(",", ".")
        elif "," in v:
            after = v.rsplit(",", 1)[-1]
            if after == "-" or not after:
                v = v.rsplit(",", 1)[0]
            elif len(after) <= 2:
                v = v.replace(",", ".")
            else:
                v = v.replace(",", "")
        try:
            result = float(v)
            return result if result > 1 else None
        except ValueError:
            return None
    return None


# Valutasymbol → ISO 4217 kode
_SYMBOL_TO_CURRENCY: dict[str, str] = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "¥": "JPY",
    "₩": "KRW",
}

_CODE_TO_CURRENCY: list[str] = [
    "EUR", "USD", "GBP", "SEK", "NOK", "CHF", "DKK",
    "CAD", "AUD", "JPY", "CNY", "PLN", "CZK", "HUF",
]


def _detect_currency(text: str) -> str:
    """
    Forsøger at genkende valutaen fra en pristreng.
    Eksempel: "€ 26,76" → "EUR",  "£12.99" → "GBP",  "749 kr." → "DKK"
    """
    for sym, code in _SYMBOL_TO_CURRENCY.items():
        if sym in text:
            return code
    upper = text.upper()
    for code in _CODE_TO_CURRENCY:
        if code in upper:
            return code
    if "KR" in upper:
        return "DKK"
    return "DKK"


def _has_currency_indicator(text: str) -> bool:
    """Returnerer True hvis teksten indeholder et genkendeligt valutasymbol eller kode."""
    for sym in _SYMBOL_TO_CURRENCY:
        if sym in text:
            return True
    upper = text.upper()
    for ind in ("KR", "DKK", "EUR", "USD", "GBP", "SEK", "NOK", "CHF", "JPY", "CAD", "AUD", "PLN", "CZK", "HUF"):
        if ind in upper:
            return True
    return False


def _deep_find(obj: Any, keys: frozenset[str], max_depth: int = 8, _d: int = 0) -> list[Any]:
    """Find alle værdier for de givne (lowercase) nøgler i en nested JSON-struktur."""
    if _d > max_depth:
        return []
    results: list[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in keys:
                results.append(v)
            else:
                results.extend(_deep_find(v, keys, max_depth, _d + 1))
    elif isinstance(obj, list):
        for item in obj[:30]:
            results.extend(_deep_find(item, keys, max_depth, _d + 1))
    return results


_STOCK_IN = frozenset({
    "instock", "in_stock", "in stock", "pålagervarer", "på lager",
    "available", "instoreonly", "onlineonly", "limitedavailability",
})
_STOCK_OUT = frozenset({
    "outofstock", "out_of_stock", "ikke på lager", "udsolgt",
    "unavailable", "discontinued", "soldout",
})
_STOCK_PRE = frozenset({"preorder", "preordering"})
_STOCK_BACK = frozenset({"backorder", "backordered"})


def _normalize_stock(v: Any) -> str | None:
    if isinstance(v, bool):
        return "in_stock" if v else "out_of_stock"
    if isinstance(v, int):
        return "in_stock" if v > 0 else "out_of_stock"
    if isinstance(v, str):
        t = (
            v.lower()
            .replace("https://schema.org/", "")
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )
        if any(x.replace(" ", "").replace("-", "").replace("_", "") in t for x in _STOCK_IN):
            return "in_stock"
        if any(x.replace(" ", "").replace("-", "").replace("_", "") in t for x in _STOCK_OUT):
            return "out_of_stock"
        if any(x.replace(" ", "").replace("-", "").replace("_", "") in t for x in _STOCK_PRE):
            return "preorder"
        if any(x.replace(" ", "").replace("-", "").replace("_", "") in t for x in _STOCK_BACK):
            return "backorder"
    return None


_PRICE_KEYS = frozenset({
    "price", "priceamount", "pricevalue", "currentprice", "sellingprice",
    "grossprice", "saleprice", "finalprice", "amount",
})
_STOCK_KEYS = frozenset({
    "availability", "stockstatus", "instock", "isinstock",
    "isavailable", "stock", "available",
})


class InlineJsonParser(PriceParser):
    """
    Udtrækker pris og lagerstatus fra indlejrede JSON-blobs i HTML.

    Understøtter datakilder i prioriteret rækkefølge:
    1. Next.js __NEXT_DATA__ — dækker elgiganten.dk og andre Next.js-shops
    2. Magento 2 x-magento-init — dækker elsalg.dk, compumail.dk m.fl.
    3. Google Tag Manager dataLayer — universelt backup
    4. OG-meta og microdata — universelt fallback
    5. window.__INITIAL_STATE__ — ikke-Next.js React-apps (biltema m.fl.)

    Bruges som fallback-extractor i scraper-pipeline'en, EFTER JSON-LD
    og shop-specifik parser.
    """

    parser_name = "inline_json"

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        result = self._try_next_data(soup)
        if result and result.success:
            return result

        result = self._try_magento_init(soup)
        if result and result.success:
            return result

        result = self._try_data_layer(soup)
        if result and result.success:
            return result

        # Strategi 4: OG-meta og microdata — universelt fallback til næsten alle butikssystemer
        result = self._try_og_and_microdata(soup)
        if result and result.success:
            return result

        # Strategi 5: window.__INITIAL_STATE__ — ikke-Next.js React-apps
        result = self._try_initial_state(soup)
        if result and result.success:
            return result

        return ParseResult(error="inline_json: ingen data fundet", parser_used=self.parser_name)

    # ── Next.js __NEXT_DATA__ ─────────────────────────────────────────────────

    def _try_next_data(self, soup: BeautifulSoup) -> ParseResult | None:
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            return None
        try:
            data = json.loads(tag.get_text())
        except (json.JSONDecodeError, ValueError):
            return None

        page_props = (data.get("props") or {}).get("pageProps") or {}
        price = self._price_from_props(page_props)

        # Fallback: scan hele __NEXT_DATA__ med større dybde
        # (fanger shops der gemmer pris udenfor pageProps, f.eks. Matas)
        if price is None:
            all_prices = [
                _clean_price(p)
                for p in _deep_find(data, _PRICE_KEYS, max_depth=12)
            ]
            valid = [p for p in all_prices if p and p > 5]
            if valid:
                price = min(valid)

        if price is None:
            return None

        return ParseResult(
            price=price,
            currency="DKK",
            stock_status=self._stock_from_props(page_props),
            title=self._title_from_props(page_props),
            parser_used=f"{self.parser_name}:next_data",
        )

    def _price_from_props(self, props: dict) -> float | None:
        # Elkjøp/Elgiganten: product.priceValue / product.price / product.grossPrice
        product = props.get("product") or props.get("item") or props.get("pdp") or {}
        for key in ("priceValue", "price", "priceAmount", "currentPrice",
                    "grossPrice", "sellingPrice", "salesPrice"):
            p = _clean_price(product.get(key) or props.get(key))
            if p:
                return p

        # offers-array (schema.org-stil i Next.js)
        offers = props.get("offers") or product.get("offers") or []
        if isinstance(offers, list) and offers:
            p = _clean_price((offers[0] or {}).get("price"))
            if p:
                return p

        # Deep search som allersidste forsøg
        for v in _deep_find(props, _PRICE_KEYS, max_depth=6):
            p = _clean_price(v)
            if p:
                return p
        return None

    def _stock_from_props(self, props: dict) -> str | None:
        product = props.get("product") or props.get("item") or props.get("pdp") or {}
        for key in ("availability", "stockStatus", "inStock", "isInStock", "isAvailable", "stock"):
            v = product.get(key) if product.get(key) is not None else props.get(key)
            if v is not None:
                s = _normalize_stock(v)
                if s:
                    return s
        for v in _deep_find(props, _STOCK_KEYS, max_depth=6):
            s = _normalize_stock(v)
            if s:
                return s
        return None

    def _title_from_props(self, props: dict) -> str | None:
        product = props.get("product") or props.get("item") or props.get("pdp") or {}
        for key in ("name", "title", "productName", "displayName"):
            v = product.get(key) or props.get(key)
            if isinstance(v, str) and len(v) > 3:
                return v
        return None

    # ── Magento 2 x-magento-init ──────────────────────────────────────────────

    def _try_magento_init(self, soup: BeautifulSoup) -> ParseResult | None:
        """
        Magento 2 embeds price configuration in:
        <script type="text/x-magento-init">
        {
          "[data-role=priceBox][data-product-id=XXXXX]": {
            "priceBox": {
              "priceConfig": {
                "prices": { "finalPrice": {"amount": 1299.00} }
              }
            }
          }
        }
        </script>
        """
        best_price: float | None = None
        best_stock: str | None = None

        for script in soup.find_all("script", attrs={"type": "text/x-magento-init"}):
            try:
                data = json.loads(script.get_text())
            except (json.JSONDecodeError, ValueError):
                continue

            # finalPrice / specialPrice → {"amount": N}
            for v in _deep_find(data, frozenset({"finalprice", "specialprice", "saleprice"}), max_depth=10):
                if isinstance(v, dict):
                    p = _clean_price(v.get("amount") or v.get("value"))
                else:
                    p = _clean_price(v)
                if p:
                    best_price = best_price or p
                    break

            # Fallback: prices-dict { "finalPrice": {"amount": N}, ... }
            if best_price is None:
                for prices in _deep_find(data, frozenset({"prices"}), max_depth=8):
                    if not isinstance(prices, dict):
                        continue
                    for _, pd in prices.items():
                        if isinstance(pd, dict):
                            p = _clean_price(pd.get("amount") or pd.get("value"))
                            if p:
                                best_price = p
                                break
                    if best_price:
                        break

            # Stock
            if best_stock is None:
                for v in _deep_find(data, frozenset({"isavailable", "isinstock", "stockstatus"}), max_depth=10):
                    s = _normalize_stock(v)
                    if s:
                        best_stock = s
                        break

        if best_price:
            return ParseResult(
                price=best_price,
                currency="DKK",
                stock_status=best_stock,
                parser_used=f"{self.parser_name}:magento_init",
            )
        return None

    # ── Google Tag Manager dataLayer ──────────────────────────────────────────

    def _try_data_layer(self, soup: BeautifulSoup) -> ParseResult | None:
        """
        GTM dataLayer indeholder ofte ecommerce-produkt-data i event-pushes.
        Standard GA4: ecommerce.items[0].price
        UA standard:  ecommerce.detail.products[0].price
        """
        _DL_RE = re.compile(r"dataLayer\s*\.push\s*\(\s*(\{.+?\})\s*\)", re.DOTALL)
        for script in soup.find_all("script"):
            text = script.get_text()
            if "dataLayer" not in text or "ecommerce" not in text:
                continue
            for m in _DL_RE.finditer(text):
                try:
                    blob = json.loads(m.group(1))
                except (json.JSONDecodeError, ValueError):
                    continue
                ecomm = blob.get("ecommerce") or {}
                products = (
                    ecomm.get("items")
                    or (ecomm.get("detail") or {}).get("products")
                    or ecomm.get("products")
                    or []
                )
                if isinstance(products, list) and products:
                    p = _clean_price(products[0].get("price"))
                    if p:
                        return ParseResult(
                            price=p,
                            currency="DKK",
                            parser_used=f"{self.parser_name}:datalayer",
                        )
        return None

    # ── OG-meta + microdata ───────────────────────────────────────────────────

    def _try_og_and_microdata(self, soup: BeautifulSoup) -> ParseResult | None:
        """
        Universelt fallback der virker på næsten alle butikssystemer:
        1. <meta property="og:price:amount">  (OpenGraph — WC, Shopify, Dandomain, …)
        2. [itemprop="price"]                 (schema.org microdata — mange CMS)
        3. [data-price] attribut              (custom shops)
        """
        # 1. OpenGraph-pris
        meta = soup.find("meta", property="og:price:amount")
        if meta and meta.get("content"):
            price = _clean_price(meta["content"])
            if price:
                title_meta = soup.find("meta", property="og:title")
                title = title_meta.get("content") if title_meta else None
                return ParseResult(
                    price=price,
                    currency="DKK",
                    title=title,
                    parser_used=f"{self.parser_name}:og_meta",
                )

        # 2. Meta product:price:amount (OpenGraph Products-namespace — Facebook Commerce)
        meta = soup.find("meta", property="product:price:amount")
        if meta and meta.get("content"):
            price = _clean_price(meta["content"])
            if price:
                title_meta = soup.find("meta", property="og:title")
                title = title_meta.get("content") if title_meta else None
                return ParseResult(
                    price=price,
                    currency="DKK",
                    title=title,
                    parser_used=f"{self.parser_name}:og_product_meta",
                )

        # 3. Schema.org microdata [itemprop="price"]
        tag = soup.find(attrs={"itemprop": "price"})
        if tag:
            price = _clean_price(tag.get("content") or tag.get_text())
            if price:
                title_tag = soup.find(attrs={"itemprop": "name"})
                title = title_tag.get_text(strip=True) if title_tag else None
                return ParseResult(
                    price=price,
                    currency="DKK",
                    title=title,
                    parser_used=f"{self.parser_name}:microdata",
                )

        # 4. [data-price] attribut
        tag = soup.find(attrs={"data-price": True})
        if tag:
            price = _clean_price(tag["data-price"])
            if price:
                return ParseResult(
                    price=price,
                    currency="DKK",
                    parser_used=f"{self.parser_name}:data_price",
                )

        return None

    # ── window.__INITIAL_STATE__ ──────────────────────────────────────────────

    def _try_initial_state(self, soup: BeautifulSoup) -> ParseResult | None:
        """
        Ikke-Next.js React-apps (f.eks. biltema.dk) gemmer ofte initial data i
        window.__INITIAL_STATE__ = {...};  i et inline <script>-tag.
        """
        _decoder = json.JSONDecoder()
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
            prices = [
                _clean_price(p)
                for p in _deep_find(data, _PRICE_KEYS, max_depth=10)
            ]
            valid = [p for p in prices if p and p > 1]
            if not valid:
                # Køer også STOCK-lignende price keys med bredere søgning
                prices2 = [
                    _clean_price(p)
                    for p in _deep_find(
                        data,
                        frozenset({"price", "priceincvat", "salesprice", "currentprice",
                                   "listprice", "retailprice", "displayprice"}),
                        max_depth=12,
                    )
                ]
                valid = [p for p in prices2 if p and p > 1]
            if valid:
                return ParseResult(
                    price=min(valid),
                    currency="DKK",
                    parser_used=f"{self.parser_name}:initial_state",
                )
        return None
