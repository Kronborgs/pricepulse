from __future__ import annotations

"""
GenericShopParser — bredt net af selectors og heuristikker baseret på erfaring
fra alle eksisterende shop-parsers. Bruges som step 5 fallback for ukendte shops.

Strategi (kører i rækkefølge, returnerer ved første hit):
  A. microdata (itemprop=price)
  B. common data-attributter (data-price, data-product-price, data-amount)
  C. open graph + regex-pris i tekst
  D. bred CSS scan: klasser med "price" i navn → regexp-validering
  E. side-tekst regexp med kr/DKK kontekst
"""

import re
from bs4 import BeautifulSoup
import structlog

from app.scraper.parsers.inline_json_parser import _clean_price, _normalize_stock
from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()

# Regexp der matcher danske/nordiske priser i fri tekst
_PRICE_RE = re.compile(
    r"""
    (?<!\d)
    (\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?)   # 1.299,00 / 1 299,00 / 12345
    |
    (\d{1,6})(?:,-)?                          # 949,- / 949
    (?=\s*(?:kr\.?|DKK|,-)\b)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# CSS-selectors der typisk indeholder pris-tekst (ikke i attribut)
_PRICE_TEXT_SELECTORS = [
    # Schema.org microdata
    "[itemprop='price']",
    "[itemprop='offers'] [itemprop='price']",
    # WooCommerce
    ".woocommerce-Price-amount",
    ".price .amount",
    "bdi",                      # WooCommerce pris-element
    # Generiske mønstre
    "[class*='price__amount']",
    "[class*='amount__price']",
    "[class*='product-price__value']",
    "[class*='price-value']",
    "[class*='PriceValue']",
    "[class*='PriceAmount']",
    "[class*='current-price']",
    "[class*='CurrentPrice']",
    "[class*='sale-price']",
    "[class*='final-price']",
    "[class*='ProductPrice']",
    # Magento
    ".price-wrapper .price",
    "[data-price-type='finalPrice'] .price",
    # Shopify
    ".product__price",
    ".price__regular",
    ".price__sale",
    # Sikker bred fallback
    "span[class*='price']",
    "div[class*='price'] span",
    "p[class*='price']",
]

# data-attributter der direkte indeholder prisen som tal
_PRICE_ATTR_SELECTORS = [
    ("[data-price]", "data-price"),
    ("[data-product-price]", "data-product-price"),
    ("[data-amount]", "data-amount"),
    ("[data-final-price]", "data-final-price"),
    ("[data-regular-price]", "data-regular-price"),
    ("[data-sale-price]", "data-sale-price"),
    ("[itemprop='price'][content]", "content"),
]

# Titel-selectors
_TITLE_SELECTORS = [
    "[itemprop='name']",
    "h1[class*='product']",
    "h1[class*='title']",
    "h1[class*='name']",
    ".product-title h1",
    ".product-name h1",
    "h1",
]

# Lager-selectors og tekst
_STOCK_SELECTORS = [
    "[itemprop='availability']",
    "[class*='stock-status']",
    "[class*='StockStatus']",
    "[class*='availability']",
    "[class*='in-stock']",
    "[class*='InStock']",
    "[class*='out-of-stock']",
    "[class*='OutOfStock']",
    "[data-stock-status]",
    ".stock",
]
_IN_STOCK_TEXTS = frozenset({
    "på lager", "in stock", "instock", "available", "in_stock",
    "tilgængelig", "få på lager", "in stock (limited)",
})
_OUT_STOCK_TEXTS = frozenset({
    "udsolgt", "ikke på lager", "out of stock", "outofstock", "unavailable",
    "out_of_stock", "utilgængelig",
})

# Billede-selectors
_IMAGE_SELECTORS = [
    "meta[property='og:image']",
    "[itemprop='image']",
    "[class*='product'] img[src*='product']",
    "[class*='ProductImage'] img",
    "[class*='gallery'] img",
    ".product-image img",
    "img[itemprop='image']",
]


class GenericShopParser(PriceParser):
    """
    Bred fallback-parser til ukendte shops.
    Kombinerer microdata, data-attributter, OG, CSS-klasse-mønstre og tekst-regexp.
    Returnerer kun resultat hvis mindst pris er fundet.
    """

    parser_name = "generic_shop"

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")

        price = (
            self._from_attr(soup)
            or self._from_text_selectors(soup)
            or self._from_og_plus_regex(soup)
            or self._from_broad_text(soup, url)
        )

        if price is None:
            return ParseResult(
                error="generic_shop: ingen pris fundet med bred scanning",
                parser_used=self.parser_name,
            )

        title = self._extract_title(soup)
        stock = self._extract_stock(soup)
        image = self._extract_image(soup)

        logger.info(
            "GenericShopParser: pris fundet",
            url=url,
            price=price,
            title=title,
        )

        return ParseResult(
            title=title,
            price=price,
            currency="DKK",
            stock_status=stock,
            image_url=image,
            parser_used=self.parser_name,
        )

    # ── Private metoder ─────────────────────────────────────────────────────

    def _from_attr(self, soup: BeautifulSoup) -> float | None:
        """Strategi A+B: microdata content og data-* attributter."""
        for selector, attr in _PRICE_ATTR_SELECTORS:
            el = soup.select_one(selector)
            if el:
                raw = el.get(attr, "")
                price = _clean_price(raw)
                if price and price > 1:
                    return price
        return None

    def _from_text_selectors(self, soup: BeautifulSoup) -> float | None:
        """Strategi C: prøv kendte CSS-klasse-mønstre, valider med regexp."""
        for sel in _PRICE_TEXT_SELECTORS:
            try:
                el = soup.select_one(sel)
            except Exception:
                continue
            if not el:
                continue
            text = el.get_text(strip=True)
            price = _clean_price(text)
            if price and 1 < price < 1_000_000:
                return price
        return None

    def _from_og_plus_regex(self, soup: BeautifulSoup) -> float | None:
        """Strategi D: brug og:price:amount eller og:price meta-tag."""
        for prop in ("product:price:amount", "og:price:amount"):
            tag = soup.find("meta", property=prop)
            if tag:
                price = _clean_price(tag.get("content", ""))
                if price and price > 1:
                    return price
        return None

    def _from_broad_text(self, soup: BeautifulSoup, url: str) -> float | None:
        """
        Strategi E: regexp i hele body-teksten — søg efter pris tæt på 'kr' / 'DKK'.
        Validerer at der eksisterer mindst ét match. Vælger den "mest fremtrædende"
        pris (den der optræder i et tag med 'price' i class-navn).
        """
        # Smal søgning: kun i elementer med 'price' i class
        for el in soup.find_all(True):
            cls = " ".join(el.get("class", []))
            if "price" not in cls.lower():
                continue
            text = el.get_text(strip=True)
            m = _PRICE_RE.search(text)
            if m:
                raw = m.group(0).rstrip(",").rstrip("-")
                price = _clean_price(raw)
                if price and 1 < price < 1_000_000:
                    return price
        # Bred søgning: hele tekst nær "kr"
        body = soup.get_text(" ", strip=True)
        for m in _PRICE_RE.finditer(body):
            raw = m.group(0).rstrip(",").rstrip("-")
            price = _clean_price(raw)
            if price and 10 < price < 500_000:
                return price
        return None

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        for sel in _TITLE_SELECTORS:
            try:
                el = soup.select_one(sel)
            except Exception:
                continue
            if el:
                t = el.get_text(strip=True)
                if 3 < len(t) < 300:
                    return t
        return None

    def _extract_stock(self, soup: BeautifulSoup) -> str | None:
        for sel in _STOCK_SELECTORS:
            try:
                el = soup.select_one(sel)
            except Exception:
                continue
            if not el:
                continue
            # itemprop="availability" — content-attribut er schema.org URL
            content = el.get("content", "")
            if content:
                if "InStock" in content:
                    return "in_stock"
                if "OutOfStock" in content:
                    return "out_of_stock"
            text = el.get_text(strip=True).lower()
            ns = _normalize_stock(text)
            if ns:
                return ns
        return None

    def _extract_image(self, soup: BeautifulSoup) -> str | None:
        for sel in _IMAGE_SELECTORS:
            try:
                el = soup.select_one(sel)
            except Exception:
                continue
            if not el:
                continue
            src = el.get("content") or el.get("src") or el.get("data-src")
            if src and src.startswith("http"):
                return src
        return None


# Singleton til brug i engine
_generic_parser = GenericShopParser()
