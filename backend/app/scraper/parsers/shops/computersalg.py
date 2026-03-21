from __future__ import annotations

from app.scraper.parsers.css_selector_parser import CssSelectorParser, SelectorConfig
from app.scraper.providers.base import ParseResult, PriceParser


class ComputersalgParser(PriceParser):
    parser_name = "computersalg"

    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=".product-price, .price-now, [itemprop='price']",
            title_selector="h1[itemprop='name'], .product-title h1",
            stock_selector=".delivery-text, .stock-status",
            image_selector=".product-image img",
            stock_in_text="på lager",
            stock_out_text="udsolgt",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result


class ELsalgParser(PriceParser):
    """
    Parser til elsalg.dk (Euronics-franchise, Magento 2 platform).

    Forsøger tre strategier i rækkefølge:
    1. data-price-amount attribut på [data-price-type="finalPrice"] — Magento standard
    2. Tekstindhold af .price inde i price-box — Magento fallback
    3. meta[itemprop="price"] content — microdata fallback
    """

    parser_name = "elsalg"

    # Strategy 1: Magento data-price-amount attribute (numeric, no formatting)
    _strategy_amount = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-price-type='finalPrice'], [data-price-type='minPrice']",
            price_attr="data-price-amount",
            title_selector="h1.page-title .base, h1.page-title, h1[itemprop='name']",
            stock_selector=".availability, .stock, .product-info-stock-sku .stock",
            image_selector=".product.media img.gallery-placeholder__image, .fotorama__img",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    # Strategy 2: Magento price text (handles "5.599 kr." via fixed price parser)
    _strategy_text = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-price-type='finalPrice'] .price, .price-box .price, .price-to-pay .price",
            title_selector="h1.page-title .base, h1.page-title, h1[itemprop='name']",
            stock_selector=".availability, .stock",
            image_selector=".product.media img, .fotorama__img",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    # Strategy 3: Microdata (meta tag with content attribute)
    _strategy_microdata = CssSelectorParser(
        SelectorConfig(
            price_selector="meta[itemprop='price']",
            price_attr="content",
            title_selector="h1[itemprop='name'], h1.page-title",
        )
    )

    # Strategy 4: Bredere Magento-selector — kun data-price-amount attribut,
    # uanset data-price-type. Fanger tilfælde med anderledes type-navne.
    _strategy_any_amount = CssSelectorParser(
        SelectorConfig(
            price_selector="[data-price-amount][data-price-type]",
            price_attr="data-price-amount",
            title_selector="h1.page-title .base, h1.page-title, h1[itemprop='name'], h1",
        )
    )

    # Strategy 5: Magento produkt-pris via id-præfix (#product-price-NNNN)
    _strategy_product_price_id = CssSelectorParser(
        SelectorConfig(
            price_selector="[id^='product-price-']",
            price_attr="data-price-amount",
            title_selector="h1.page-title .base, h1.page-title, h1",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        for parser in (
            self._strategy_amount,
            self._strategy_text,
            self._strategy_microdata,
            self._strategy_any_amount,
            self._strategy_product_price_id,
        ):
            result = parser.parse(content, url)
            if result.success:
                result.parser_used = self.parser_name
                return result
        return ParseResult(
            error="elsalg: ingen Magento-selector matchede",
            parser_used=self.parser_name,
        )


class HappiiParser(PriceParser):
    parser_name = "happii"

    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=".price--sale .price__item, .price__item--regular",
            title_selector=".product__title h1, h1.title",
            stock_selector=".product-availability",
            stock_in_text="på lager",
            stock_out_text="udsolgt",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result


class KomplettParser(PriceParser):
    """
    Parser til komplett.dk.
    Komplett anvender aktiv bot-beskyttelse (HTTP/2 stream reset + challenge-sider).
    Kræver Playwright for pålidelig scraping — se PLAYWRIGHT_REQUIRED_DOMAINS.
    CSS selectors forsøges som fallback, hvis HTTP-siden alligevel leveres.
    """

    parser_name = "komplett"

    _css_primary = CssSelectorParser(
        SelectorConfig(
            # Komplett viste klasserne .product-price-now/.price-now i ældre design.
            # Nyere design bruger data-testid og andre klasse-mønstre.
            price_selector=(
                ".product-price-now, "
                ".price-now span, "
                "[data-testid='price'], "
                "[data-testid='product-price'], "
                "span[class*='product-price'], "
                "span[class*='ProductPrice']"
            ),
            title_selector="h1.product-main-name, h1[class*='product'], h1",
            stock_selector=".stock-status-container, [data-testid='stock-status']",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_primary.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result

