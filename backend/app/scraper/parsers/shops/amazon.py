from __future__ import annotations

import re

import structlog
from bs4 import BeautifulSoup

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.parsers.inline_json_parser import _clean_price, _detect_currency, _has_currency_indicator
from app.scraper.providers.base import ErrorType, ParseResult, PriceParser

logger = structlog.get_logger()

# ASIN fra URL: /dp/B0BVTSVQVQ eller /gp/product/B0BVTSVQVQ
_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")

# Amazon domæne → valutakode
_DOMAIN_CURRENCY: dict[str, str] = {
    "amazon.nl": "EUR",
    "amazon.de": "EUR",
    "amazon.fr": "EUR",
    "amazon.es": "EUR",
    "amazon.it": "EUR",
    "amazon.at": "EUR",
    "amazon.be": "EUR",
    "amazon.pl": "PLN",
    "amazon.se": "SEK",
    "amazon.co.uk": "GBP",
    "amazon.co.jp": "JPY",
    "amazon.ca": "CAD",
    "amazon.com.au": "AUD",
    "amazon.com.br": "BRL",
    "amazon.com.mx": "MXN",
    "amazon.com": "USD",
    "amazon.in": "INR",
}


def _currency_from_url(url: str) -> str:
    """Udled valutakode fra Amazon-domæne (f.eks. amazon.nl → EUR)."""
    url_lower = url.lower()
    for domain, code in _DOMAIN_CURRENCY.items():
        if domain in url_lower:
            return code
    return "DKK"


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

        # Sandvagt: Amazons statiske HTML er typisk 100-500 KB.
        # En respons under 15 KB er en bot-afvisningsside (returnerer 200 men intet produkt).
        # Returnér en specifik fejl så at parseren korrekt signalerer "prøv Chrome-TLS" eller
        # "prøv Browser/JS" i stedet for at falde igennem til GenericShopParser.
        if len(content) < 15_000:
            logger.info(
                "amazon: HTML for lille — sandsynlig bot-afvisning",
                html_bytes=len(content), url=url,
            )
            return ParseResult(
                error="amazon: HTML for lille (bot-afvisning?). Prøv Chrome-TLS eller Browser/JS.",
                error_type=ErrorType.bot_protection,
                recommended_action="Siden afviser HTTP-scraping. Skift til Chrome-TLS eller Browser/JS.",
                parser_used=self.parser_name,
            )

        # Strategi 0: Twister-data — priser i statisk HTML, ingen Playwright nødvendig
        result = self._try_twister_data(content, url, soup)
        if result:
            return result

        # Strategi 1: a-price-whole + a-price-fraction (statisk HTML, ingen JS nødvendig)
        result = self._try_price_parts(soup, url)
        if result:
            return result

        # Strategi 2-3: CSS (virker kun efter Playwright-rendering)
        result = self._css_primary.parse(content, url)
        if result.success and result.price and result.price > 1:
            result.parser_used = self.parser_name
            # Forsøg at finde valuta fra buy-box tekst; fald tilbage til domænekort
            result.currency = self._detect_currency_from_soup(soup, url)
            logger.debug("amazon: pris fundet via CSS (Playwright)", price=result.price, currency=result.currency, url=url)
            return result

        # Strategi 4: Manuel scan af a-offscreen i buy-box containere
        price, currency = self._scan_offscreen_spans(soup, url)
        if price and price > 1:
            title_tag = soup.select_one("#productTitle")
            stock_tag = soup.select_one("#availability span, #availability")
            img_tag = soup.select_one("#landingImage")
            return ParseResult(
                price=price,
                currency=currency,
                title=title_tag.get_text(strip=True) if title_tag else None,
                stock_status=stock_tag.get_text(strip=True) if stock_tag else None,
                image_url=img_tag.get("src") if img_tag else None,
                parser_used=self.parser_name,
            )

        return ParseResult(
            error="amazon: ingen pris fundet i twister-data eller buy-box",
            parser_used=self.parser_name,
        )

    def _try_price_parts(self, soup: BeautifulSoup, url: str) -> ParseResult | None:
        """
        Statisk HTML strategi: kombiner a-price-whole + a-price-fraction.

        Amazon's priser vises sådan i HTML (også uden JS):
          <span class="a-price-whole">15</span>
          <span class="a-price-fraction">50</span>
        Begge er i statisk HTML og er særdelst pålidelige når de er til stede.
        """
        # Begræns søgning til buy-box området hvis muligt
        container = soup.select_one(
            "#corePriceDisplay_desktop_feature_div, #apexPriceToPay, "
            "#corePrice_feature_div, #centerCol, #rightCol"
        )
        root = container if container else soup

        whole_tag = root.select_one("span.a-price-whole")
        frac_tag = root.select_one("span.a-price-fraction")
        if not whole_tag:
            return None

        # Ryd op: fjern decimal-separator-element inde i whole (typisk `<span class='a-price-decimal'>.</span>`)
        decimal_sep = whole_tag.select_one(".a-price-decimal")
        if decimal_sep:
            decimal_sep.extract()

        whole_text = whole_tag.get_text(strip=True).replace(".", "").replace(",", "")
        frac_text = frac_tag.get_text(strip=True) if frac_tag else "00"
        frac_text = frac_text[:2]  # maks 2 decimaler

        try:
            price = float(f"{whole_text}.{frac_text}")
        except ValueError:
            return None

        if not price or price <= 1:
            return None

        currency = _currency_from_url(url)
        title_tag = soup.select_one("#productTitle")
        stock_tag = soup.select_one("#availability span, #availability")
        img_tag = soup.select_one("#landingImage")

        logger.info("amazon: pris fundet via a-price-whole/fraction", price=price, currency=currency, url=url)
        return ParseResult(
            price=price,
            currency=currency,
            title=title_tag.get_text(strip=True) if title_tag else None,
            stock_status=stock_tag.get_text(strip=True) if stock_tag else None,
            image_url=img_tag.get("src") if img_tag else None,
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

        # Søg priceWithoutCurrencySymbol inden for 2000 tegn fremad fra markøren
        window = content[marker.start(): marker.start() + 2000]
        price_match = re.search(r'"priceWithoutCurrencySymbol"\s*:\s*"([0-9]+\.[0-9]+)"', window)
        if not price_match:
            logger.debug("amazon: priceWithoutCurrencySymbol ikke fundet for ASIN", asin=asin)
            return None

        price = _clean_price(price_match.group(1))
        if not price or price <= 1:
            return None

        # currencyCode ligger typisk tæt på priseWithoutCurrencySymbol — søg i vinduer op til fund
        price_pos = price_match.start()
        currency_window = window[:price_pos + 200]
        currency_match = re.search(r'"currencyCode"\s*:\s*"([A-Z]{3})"', currency_window)
        # Fallback: søg hele vinduet
        if not currency_match:
            currency_match = re.search(r'"currencyCode"\s*:\s*"([A-Z]{3})"', window)
        currency = currency_match.group(1) if currency_match else _currency_from_url(url)

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

        logger.info("amazon: twister-data pris fundet", asin=asin, price=price, currency=currency, url=url)
        return ParseResult(
            price=price,
            currency=currency,
            title=title_tag.get_text(strip=True) if title_tag else None,
            image_url=img_tag.get("src") if img_tag else None,
            parser_used=self.parser_name,
        )

    def _detect_currency_from_soup(self, soup: BeautifulSoup, url: str) -> str:
        """
        Scanner buy-box .a-offscreen spans for valutaindikatorer.
        Falder tilbage til domænekort hvis ingen indikator findes i teksten.
        """
        containers = soup.select(
            "#buybox, #centerCol, #apex_desktop, #corePriceDisplay_desktop_feature_div"
        )
        search_root = containers[0] if containers else soup
        for span in search_root.select(".a-offscreen"):
            raw = span.get_text(strip=True)
            if _has_currency_indicator(raw):
                return _detect_currency(raw)
        return _currency_from_url(url)

    def _scan_offscreen_spans(self, soup: BeautifulSoup, url: str) -> tuple[float | None, str]:
        """Scan .a-offscreen spans i buy-box containere — fallback til Playwright."""
        containers = soup.select(
            "#buybox, #centerCol, #apex_desktop, #corePriceDisplay_desktop_feature_div"
        )
        search_root = containers[0] if containers else soup
        for span in search_root.select(".a-offscreen"):
            raw = span.get_text(strip=True)
            price = _clean_price(raw)
            if price and price > 1:
                # Brug tekst-baseret valutadetektion; fald kun tilbage til domæne
                # hvis ingen indikator (€, kr., DKK osv.) er til stede i teksten
                currency = _detect_currency(raw) if _has_currency_indicator(raw) else _currency_from_url(url)
                return price, currency
        return None, _currency_from_url(url)

