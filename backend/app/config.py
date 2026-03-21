from __future__ import annotations

import logging
from typing import Literal

import structlog
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────
    environment: Literal["development", "production"] = "production"
    secret_key: str = "insecure-dev-key-change-me"
    log_level: str = "INFO"

    # ─── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://pricepulse:changeme@db:5432/pricepulse"

    # ─── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ─── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ─── Scraper ──────────────────────────────────────────────
    scraper_domain_delay: float = 5.0          # sekunder mellem requests til samme domæne
    scraper_max_concurrent: int = 4            # max antal parallelle scrapes
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
    playwright_enabled: bool = False           # kræver Playwright installation

    # ─── Ollama ────────────────────────────────────────────────
    ollama_enabled: bool = True
    ollama_host: str = "http://10.10.80.10:11434"
    ollama_parser_model: str = "qwen2.5:7b-instruct-q4_K_M"
    ollama_normalize_model: str = "qwen2.5:7b-instruct-q4_K_M"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_timeout: int = 30
    # Cache LLM-resultater i antal sekunder (24 timer standard)
    ollama_cache_ttl: int = 86400

    # ─── Scheduler ────────────────────────────────────────────
    scheduler_default_interval_minutes: int = 60

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper


settings = Settings()


def configure_logging() -> None:
    """Sæt structlog op til JSON output i prod, pretty i dev."""
    log_level = getattr(logging, settings.log_level)
    logging.basicConfig(level=log_level)

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


configure_logging()
