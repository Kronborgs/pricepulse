"""Persistent Ollama configuration stored alongside PricePulse app data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

CONFIG_FILE = Path("/app/data/ollama_config.json")
_CONFIG_FIELDS = ("enabled", "host", "parser_model", "normalize_model", "embed_model")


async def load_persisted_config() -> dict[str, Any]:
    """Load user-selected Ollama settings without failing application startup."""
    try:
        async with aiofiles.open(CONFIG_FILE, "r", encoding="utf-8") as file:
            payload = json.loads(await file.read())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("ollama_config_load_failed", error=str(exc))
        return {}

    return payload if isinstance(payload, dict) else {}


async def apply_persisted_config() -> None:
    """Apply persisted settings after environment defaults have been loaded."""
    payload = await load_persisted_config()
    for field in _CONFIG_FIELDS:
        if field in payload and payload[field] is not None:
            setattr(settings, f"ollama_{field}", payload[field])


async def save_persisted_config() -> None:
    """Persist the current Ollama settings on the durable app-data mount."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        field: getattr(settings, f"ollama_{field}")
        for field in _CONFIG_FIELDS
    }
    async with aiofiles.open(CONFIG_FILE, "w", encoding="utf-8") as file:
        await file.write(json.dumps(payload, indent=2) + "\n")