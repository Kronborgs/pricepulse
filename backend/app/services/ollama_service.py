"""
OllamaService — intelligent assist-lag til PricePulse.

Bruges til:
  - parser_advice: forslag til selectors ved parse-fejl
  - normalization: produktnormalisering (brand, model, variant, MPN)
  - embeddings: semantic similarity til produktmatchning

Design-principper:
  - Aldrig blocking for kritiske check-flows
  - Timeout 30 sek med clean fallback til None
  - Caching via llm_analysis_results (SHA256 cache_key)
  - Ingen hård afhængighed — alt er optional
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_analysis_result import LlmAnalysisResult

logger = structlog.get_logger(__name__)

# ── Ollama concurrency guard ──────────────────────────────────────────────────
# Kun ét Ollama-kald ad gangen — forhindrer timeout-kaskade når mange watches
# fejler samtidig og alle forsøger Ollama på én gang.
_ollama_busy: bool = False


def is_ollama_busy() -> bool:
    """Returner True hvis en Ollama-forespørgsel allerede kører."""
    return _ollama_busy


# ── Dataklasser for analyse-resultater ────────────────────────────────────────

@dataclass
class ParserAdvice:
    """Ollamas forslag til parser-reparation."""
    page_type: str                              # product | listing | blocked | unknown
    price_selector: str | None = None          # CSS-selektor forslag
    stock_selector: str | None = None          # CSS-selektor forslag
    requires_js: bool = False
    likely_bot_protection: bool = False
    reasoning: str = ""
    recommended_action: str = ""               # fx "Prøv playwright / Tilføj manuel selektor"
    confidence: float = 0.0


@dataclass
class NormalizedProduct:
    """Ollamas normalisering af produkttitel."""
    brand: str | None = None
    model: str | None = None
    variant: str | None = None
    mpn: str | None = None
    normalized_key: str | None = None          # brand + model + variant kombination
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class EmbeddingResult:
    vector: list[float] = field(default_factory=list)
    model: str = ""


# ── Hjælpefunktioner ──────────────────────────────────────────────────────────

def _cache_key(parts: list[str]) -> str:
    """SHA256 af sammensatte dele → 64-char hex-streng."""
    combined = "|".join(str(p) for p in parts)
    return hashlib.sha256(combined.encode()).hexdigest()


def _truncate_html(html: str, max_bytes: int = 12_000) -> str:
    """Begræns HTML-snippet til max_bytes for at holde prompt lille."""
    encoded = html.encode("utf-8")[:max_bytes]
    return encoded.decode("utf-8", errors="ignore")


def _slim_html_for_prompt(html: str, max_bytes: int = 3_500) -> str:
    """
    Reducér HTML til kun synligt DOM-indhold til Ollama-prompts.

    Fjerner <script>, <style>, <noscript>, <svg> og <footer>/<nav>/<header>
    som er irrelevante for CSS-selektor-genkendelse men fylder mange tokens.
    Derefter trunkeres til max_bytes.

    En 12KB side typisk → 4000-5000 tokens inkl. scripts.
    Efter stripping → 1000-2000 tokens, hvilket passer til 4096 context.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "footer", "nav", "header", "iframe"]):
            tag.decompose()
        slimmed = str(soup)
    except Exception:
        slimmed = html

    encoded = slimmed.encode("utf-8")[:max_bytes]
    return encoded.decode("utf-8", errors="ignore")


# ── OllamaService ─────────────────────────────────────────────────────────────

class OllamaService:
    """
    Service til kommunikation med lokal Ollama-instans.
    Alle metoder returnerer None ved fejl — de er aldrig blocking.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.ollama_host,
                timeout=settings.ollama_timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Tilgængelighed ────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Ping Ollama og returner True hvis tilgængelig."""
        if not settings.ollama_enabled:
            return False
        try:
            client = self._get_client()
            resp = await client.get("/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Returner navne på tilgængelige modeller."""
        try:
            client = self._get_client()
            resp = await client.get("/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.warning("ollama_list_models_failed", error=str(exc))
            return []

    # ── Intern: chat completion ───────────────────────────────────────────────

    async def _chat(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> dict[str, Any] | None:
        """
        Kald Ollama /api/chat.
        Returnerer parsed JSON dict (hvis json_mode=True) eller None ved fejl.
        Returnerer None straks hvis Ollama allerede er optaget (forhindrer timeout-kaskade).
        """
        global _ollama_busy
        if not settings.ollama_enabled:
            return None
        if _ollama_busy:
            logger.info("ollama_busy_skip", model=model)
            return None
        _ollama_busy = True
        try:
            client = self._get_client()
            payload: dict[str, Any] = {
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
            if json_mode:
                payload["format"] = "json"

            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count")
            response_tokens = data.get("eval_count")

            if json_mode:
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("ollama_json_parse_failed", content=content[:200])
                    return None
                return {
                    "result": result,
                    "prompt_tokens": prompt_tokens,
                    "response_tokens": response_tokens,
                }
            return {
                "result": content,
                "prompt_tokens": prompt_tokens,
                "response_tokens": response_tokens,
            }
        except httpx.TimeoutException:
            logger.warning("ollama_timeout", model=model)
            return None
        except Exception as exc:
            logger.warning("ollama_chat_failed", model=model, error=str(exc))
            return None
        finally:
            _ollama_busy = False

    # ── Cache-hjælper ─────────────────────────────────────────────────────────

    async def _get_cached(
        self, db: AsyncSession, key: str
    ) -> LlmAnalysisResult | None:
        ttl_cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.ollama_cache_ttl)
        stmt = select(LlmAnalysisResult).where(
            LlmAnalysisResult.cache_key == key,
            LlmAnalysisResult.created_at >= ttl_cutoff,
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def _save_result(
        self,
        db: AsyncSession,
        *,
        analysis_type: str,
        model_used: str,
        cache_key: str | None,
        input_data: dict,
        output_data: dict,
        confidence: float | None,
        prompt_tokens: int | None,
        response_tokens: int | None,
        source_id: str | None = None,
        watch_id: str | None = None,
    ) -> None:
        from sqlalchemy.exc import IntegrityError

        row = LlmAnalysisResult(
            source_id=source_id,
            watch_id=watch_id,
            analysis_type=analysis_type,
            model_used=model_used,
            cache_key=cache_key,
            cached=False,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
        )
        db.add(row)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            logger.warning(
                "llm_result_not_saved",
                reason="watch_deleted_or_conflict",
                watch_id=watch_id,
            )

    # ── Parser Advice ─────────────────────────────────────────────────────────

    async def analyze_parser(
        self,
        *,
        db: AsyncSession,
        url: str,
        html_snippet: str,
        html_title: str,
        status_code: int,
        failed_extractors: list[str],
        source_id: str | None = None,
        watch_id: str | None = None,
    ) -> ParserAdvice | None:
        """
        Analysér en fejlet scrape og foreslå selectors.
        Returnerer None hvis Ollama ikke er tilgængelig eller svarer forkert.
        """
        if not settings.ollama_enabled:
            return None

        key = _cache_key([url, _truncate_html(html_snippet, 4096), "parser_advice_v2"])
        cached = await self._get_cached(db, key)
        if cached:
            data = cached.output_data or {}
            return ParserAdvice(
                page_type=data.get("page_type", "unknown"),
                price_selector=data.get("price_selector"),
                stock_selector=data.get("stock_selector"),
                requires_js=bool(data.get("requires_js", False)),
                likely_bot_protection=bool(data.get("likely_bot_protection", False)),
                reasoning=data.get("reasoning", ""),
                recommended_action=data.get("recommended_action", ""),
                confidence=float(data.get("confidence", 0.0)),
            )

        system = (
            "Du er et JSON-udtræksværktøj til web-scraping. Returner KUN et JSON-objekt — ingen forklaringer, ingen kode.\n"
            "HTML-indholdet er allerede hentet og leveret. Analysér det og returner:\n"
            "  page_type (string): 'product' | 'listing' | 'blocked' | 'captcha' | 'unknown'\n"
            "  price_selector (string|null): CSS-selektor som vil finde priselementet, fx '.price' eller '[data-price]'\n"
            "  stock_selector (string|null): CSS-selektor til lagerstatus-element\n"
            "  requires_js (bool): kræver siden JavaScript-rendering for at vise prisen?\n"
            "  likely_bot_protection (bool): indikerer HTML bot-beskyttelse/CAPTCHA?\n"
            "  reasoning (string): én sætning begrundelse\n"
            "  recommended_action (string): én specifik anbefaling\n"
            "  confidence (float): 0.0-1.0\n"
            "SVAR KUN MED JSON, intet andet."
        )

        user = (
            f"URL (kun til kontekst): {url}\n"
            f"HTTP status: {status_code}\n"
            f"HTML title: {html_title}\n"
            f"Fejlede extractors: {', '.join(failed_extractors) or 'ingen'}\n\n"
            f"HTML (find CSS-selektorer til pris og lager i denne HTML):\n---\n{_slim_html_for_prompt(html_snippet)}\n---\n\n"
            f"Returner JSON nu:"
        )

        response = await self._chat(settings.ollama_parser_model, system, user)
        if not response:
            return None

        raw: dict = response["result"]
        advice = ParserAdvice(
            page_type=raw.get("page_type", "unknown"),
            price_selector=raw.get("price_selector"),
            stock_selector=raw.get("stock_selector"),
            requires_js=bool(raw.get("requires_js", False)),
            likely_bot_protection=bool(raw.get("likely_bot_protection", False)),
            reasoning=raw.get("reasoning", ""),
            recommended_action=raw.get("recommended_action", ""),
            confidence=float(raw.get("confidence", 0.0)),
        )

        await self._save_result(
            db,
            analysis_type="parser_advice",
            model_used=settings.ollama_parser_model,
            cache_key=key,
            input_data={"url": url, "status_code": status_code,
                        "html_title": html_title, "failed_extractors": failed_extractors},
            output_data=raw,
            confidence=advice.confidence,
            prompt_tokens=response.get("prompt_tokens"),
            response_tokens=response.get("response_tokens"),
            source_id=source_id,
        )
        return advice

    # ── Direkte pris-udtræk fra HTML-tekst ───────────────────────────────────

    async def extract_price_from_text(
        self,
        *,
        db: AsyncSession,
        url: str,
        html: str,
        watch_id: str | None = None,
        source_id: str | None = None,
    ) -> "ParseResult | None":
        """
        Brug LLM som tekstbaseret browser til direkte at udtrække
        pris og lager fra rå HTML-tekst — ingen CSS-selektorer.
        Returnerer None hvis Ollama ikke er tilgængelig eller ingen pris findes.
        """
        from app.scraper.providers.base import ParseResult

        if not settings.ollama_enabled:
            return None

        # Udtræk synlig tekst fra HTML.
        # Brug BeautifulSoup til at fjerne cookie-bannere, navigation og
        # layoutelementer — ellers vil de første 3-5 KB af synlig tekst
        # typisk indehold cookie-samtykkebannere frem for produktindhold.
        import re
        try:
            from bs4 import BeautifulSoup as _BS
            _soup = _BS(html, "lxml")
            # Fjern scripts, styles og sideomkransende elementer
            for _tag in _soup(["script", "style", "noscript", "svg",
                                "iframe", "footer", "nav", "header"]):
                _tag.decompose()
            # Fjern cookie-banner containere (Cookiebot, OneTrust, consentmanager m.fl.)
            _cookie_re = re.compile(
                r"cookie|consent|gdpr|CybotCookiebot|onetrust|consentmanager",
                re.IGNORECASE,
            )
            for _tag in _soup.find_all(True, attrs={"id": _cookie_re}):
                _tag.decompose()
            for _tag in _soup.find_all(True, attrs={"class": _cookie_re}):
                _tag.decompose()
            text = _soup.get_text(separator=" ", strip=True)
        except Exception:
            # Fallback til simpel regex-stripping
            text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = text[:5_000]  # 5000 chars ≈ 2000 tokens — sikkert under 4096-grænsen

        key = _cache_key([url, text[:2000], "text_extract_v2"])
        cached = await self._get_cached(db, key)
        if cached:
            raw = cached.output_data or {}
            price_val = raw.get("price")
            if price_val is None:
                return None
            return ParseResult(
                price=float(price_val),
                currency=raw.get("currency", "DKK"),
                stock_status=raw.get("stock_status"),
                title=raw.get("title"),
                parser_used="ollama_text",
            )

        system = (
            "Du er et JSON-udtræksværktøj. Returner KUN et JSON-objekt — ingen forklaringer, ingen kode, ingen tekst udenfor JSON.\n"
            "HTML-indholdet fra produktsiden er allerede hentet og leveret nedenfor.\n"
            "Din opgave: udtræk følgende fra den givne tekst:\n"
            "  price (number|null): produktprisen som decimaltal uden valutasymbol, fx 3290.0\n"
            "  currency (string): valutakode, fx 'DKK'. Standard: 'DKK'\n"
            "  stock_status (string|null): 'in_stock' hvis på lager, 'out_of_stock' hvis ikke, null hvis ukendt\n"
            "  title (string|null): produktets navn/titel\n"
            "  confidence (float): 0.0-1.0, din sikkerhed for at price er korrekt\n"
            "Regler:\n"
            "  - Find KUN den primære produktpris — ikke tilbehørspriser eller 'fra X kr.'\n"
            "  - Er det ikke en produktside, sæt price til null\n"
            "  - Forsøg IKKE at hente URLs — teksten er allerede her\n"
            "  - SVAR KUN MED JSON, intet andet"
        )

        user = (
            f"URL (kun til kontekst): {url}\n\n"
            f"SIDETEKST (udtræk price, currency, stock_status, title, confidence fra denne tekst):\n"
            f"---\n{text}\n---\n\n"
            f"Returner JSON nu:"
        )

        response = await self._chat(settings.ollama_parser_model, system, user)
        if not response:
            return None

        raw: dict = response["result"]
        price_raw = raw.get("price")
        confidence = float(raw.get("confidence", 0.0))

        await self._save_result(
            db,
            analysis_type="text_extract",
            model_used=settings.ollama_parser_model,
            cache_key=key,
            input_data={"url": url, "text_length": len(text)},
            output_data=raw,
            confidence=confidence,
            prompt_tokens=response.get("prompt_tokens"),
            response_tokens=response.get("response_tokens"),
            watch_id=watch_id,
            source_id=source_id,
        )

        if price_raw is None or confidence < 0.4:
            return None

        try:
            return ParseResult(
                price=float(price_raw),
                currency=raw.get("currency", "DKK"),
                stock_status=raw.get("stock_status"),
                title=raw.get("title"),
                parser_used="ollama_text",
            )
        except (TypeError, ValueError):
            return None

    # ── Produktnormalisering ──────────────────────────────────────────────────

    async def normalize_product(
        self,
        *,
        db: AsyncSession,
        titles: list[str],
        watch_id: str | None = None,
    ) -> NormalizedProduct | None:
        """
        Normalisér produkttitler til brand, model, variant, MPN.
        Kør ved watch-oprettelse og ved periodisk re-normalisering.
        """
        if not settings.ollama_enabled or not titles:
            return None

        key = _cache_key(sorted(titles) + ["normalization"])
        cached = await self._get_cached(db, key)
        if cached:
            data = cached.output_data or {}
            return NormalizedProduct(**{k: v for k, v in data.items()
                                        if k in NormalizedProduct.__dataclass_fields__})

        system = (
            "Du er en produktdata-ekspert. Analysér produkttitler og returner JSON:\n"
            "brand (string|null): producent/mærke\n"
            "model (string|null): modelnavn\n"
            "variant (string|null): variant (farve, størrelse, kapacitet, etc.)\n"
            "mpn (string|null): manufacturer part number / produktnummer\n"
            "normalized_key (string): brand + model + variant som key (lowercase, bindestreg)\n"
            "confidence (float 0.0-1.0)\n"
            "reasoning (string): kort begrundelse\n"
            "Svar kun med JSON."
        )

        titles_text = "\n".join(f"- {t}" for t in titles[:5])  # max 5 titler
        user = f"Produkttitler:\n{titles_text}"

        response = await self._chat(settings.ollama_normalize_model, system, user)
        if not response:
            return None

        raw: dict = response["result"]
        normalized = NormalizedProduct(
            brand=raw.get("brand"),
            model=raw.get("model"),
            variant=raw.get("variant"),
            mpn=raw.get("mpn"),
            normalized_key=raw.get("normalized_key"),
            confidence=float(raw.get("confidence", 0.0)),
            reasoning=raw.get("reasoning", ""),
        )

        await self._save_result(
            db,
            analysis_type="normalization",
            model_used=settings.ollama_normalize_model,
            cache_key=key,
            input_data={"titles": titles},
            output_data=raw,
            confidence=normalized.confidence,
            prompt_tokens=response.get("prompt_tokens"),
            response_tokens=response.get("response_tokens"),
            watch_id=watch_id,
        )
        return normalized

    # ── Embeddings ────────────────────────────────────────────────────────────

    async def get_embedding(self, text: str) -> EmbeddingResult | None:
        """
        Hent embedding-vektor for tekst via nomic-embed-text.
        Bruges til semantisk produktmatchning.
        """
        if not settings.ollama_enabled:
            return None
        try:
            client = self._get_client()
            resp = await client.post(
                "/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text[:2000]},
            )
            resp.raise_for_status()
            data = resp.json()
            return EmbeddingResult(
                vector=data.get("embedding", []),
                model=settings.ollama_embed_model,
            )
        except httpx.TimeoutException:
            logger.warning("ollama_embed_timeout")
            return None
        except Exception as exc:
            logger.warning("ollama_embed_failed", error=str(exc))
            return None

    async def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Beregn cosine similarity mellem to vektorer."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# Singleton-instans — importeres af services
ollama_service = OllamaService()
