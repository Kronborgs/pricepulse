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
    parser_name = "elsalg"

    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=".price .amount, .product-price",
            title_selector="h1.product_title",
            stock_selector=".stock",
            image_selector=".woocommerce-product-gallery__image img",
            stock_in_text="på lager",
            stock_out_text="udsolgt",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result


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
    parser_name = "komplett"

    _css_parser = CssSelectorParser(
        SelectorConfig(
            price_selector=".product-price-now, .price-now span",
            title_selector="h1.product-main-name",
            stock_selector=".stock-status-container",
            stock_in_text="på lager",
            stock_out_text="ikke på lager",
        )
    )

    def parse(self, content: str, url: str) -> ParseResult:
        result = self._css_parser.parse(content, url)
        if result.success:
            result.parser_used = self.parser_name
        return result
