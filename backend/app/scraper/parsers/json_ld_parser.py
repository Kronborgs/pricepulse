from __future__ import annotations

import json
import re
from dataclasses import dataclass

import structlog
from bs4 import BeautifulSoup

from app.scraper.providers.base import ParseResult, PriceParser

logger = structlog.get_logger()


class JsonLdParser(PriceParser):
    """
    Parser der udtrækker pris fra JSON-LD structured data (schema.org/Product).
    Den mest pålidelige metode — shop-uafhængig, fungerer på de fleste moderne webshops.
    """

    parser_name = "json_ld"

    # Priser som disse shops skriver dem: "1.299,00", "1299.00", "1 299 kr"
    PRICE_PATTERN = re.compile(r"[\d.,\s]+")

    def parse(self, content: str, url: str) -> ParseResult:
        soup = BeautifulSoup(content, "lxml")
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            # Use get_text() instead of .string — .string returns None when
            # BeautifulSoup splits a long text node into multiple NavigableStrings,
            # which silently skips large JSON-LD blocks.
            raw = script.get_text(strip=False)
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.debug("JSON-LD: parse fejl", error=str(exc))
                continue

            # Håndter både enkelt objekt og @graph array
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@graph"):
                    items.extend(item["@graph"])
                    continue

                result = self._try_extract_product(item, url)
                if result:
                    return result

        return ParseResult(error="JSON-LD: ingen schema.org/Product fundet")

    def _try_extract_product(self, data: dict, url: str) -> ParseResult | None:
        type_ = data.get("@type", "")
        if isinstance(type_, list):
            type_ = " ".join(type_)
        if "Product" not in type_:
            return None

        title = data.get("name")
        image = data.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        if isinstance(image, dict):
            image = image.get("url")

        ean = data.get("gtin13") or data.get("gtin8") or data.get("ean")

        offers = data.get("offers") or data.get("Offers")
        if not offers:
            return None

        if isinstance(offers, list):
            # Tag det første tilgængelige offer
            offers = next(
                (o for o in offers if o.get("availability", "").endswith("InStock")),
                offers[0],
            )

        price_raw = offers.get("price") or offers.get("Price")
        currency = offers.get("priceCurrency") or offers.get("PriceCurrency") or "DKK"
        availability = offers.get("availability", "")

        price = self._parse_price(price_raw)
        if price is None:
            return None

        # schema.org availability values that mean "orderable":
        # InStock, PreOrder, BackOrder, LimitedAvailability, OnlineOnly, InStoreOnly
        ORDERABLE = ("InStock", "PreOrder", "BackOrder", "LimitedAvailability", "OnlineOnly", "InStoreOnly")
        if availability:
            if any(s in availability for s in ORDERABLE):
                stock_status = "in_stock"
            else:
                stock_status = "out_of_stock"
        else:
            stock_status = None

        return ParseResult(
            title=title,
            price=price,
            currency=currency,
            stock_status=stock_status,
            image_url=image,
            ean=ean,
            parser_used=self.parser_name,
            raw_data={"type": type_, "offer": offers},
        )

    def _parse_price(self, raw: object) -> float | None:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            # Fjern valuta-symboler og whitespace
            cleaned = raw.replace("kr", "").replace("DKK", "").replace(" ", "").strip()
            # Dansk format: 1.299,00 → 1299.00
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
