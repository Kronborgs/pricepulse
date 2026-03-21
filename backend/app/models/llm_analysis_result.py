from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LlmAnalysisResult(Base):
    """
    Cache og historik for Ollama LLM-analyser.

    analysis_type:
      parser_advice     → forslag til selectors ved parse-fejl
      normalization     → produktnormalisering (brand, model, variant, MPN)
      product_matching  → sammenligning af to sources (same product?)
      debug             → fri tekstdiagnose

    cache_key = SHA256 af (url + html_snippet[:8192] + analysis_type).
    Gyldigt i 24 timer — se OllamaService for cache-logik.
    """

    __tablename__ = "llm_analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("watch_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    watch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_watches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    analysis_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    response_tokens: Mapped[int | None] = mapped_column(Integer)
    cache_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    input_data: Mapped[dict | None] = mapped_column(JSONB)
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
