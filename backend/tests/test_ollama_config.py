from __future__ import annotations

import json

import pytest

from app.config import settings
from app.services import ollama_config


@pytest.mark.asyncio
async def test_ollama_config_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / "ollama_config.json"
    monkeypatch.setattr(ollama_config, "CONFIG_FILE", config_path)

    settings.ollama_enabled = False
    settings.ollama_host = "http://10.10.80.70:11434"
    settings.ollama_parser_model = "parser-model"
    settings.ollama_normalize_model = "normalizer-model"
    settings.ollama_embed_model = "embedding-model"

    await ollama_config.save_persisted_config()

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["host"] == "http://10.10.80.70:11434"

    settings.ollama_host = "http://old-host:11434"
    settings.ollama_enabled = True
    await ollama_config.apply_persisted_config()

    assert settings.ollama_enabled is False
    assert settings.ollama_host == "http://10.10.80.70:11434"
    assert settings.ollama_parser_model == "parser-model"
    assert settings.ollama_normalize_model == "normalizer-model"
    assert settings.ollama_embed_model == "embedding-model"


@pytest.mark.asyncio
async def test_missing_and_invalid_ollama_config_are_ignored(tmp_path, monkeypatch):
    config_path = tmp_path / "ollama_config.json"
    monkeypatch.setattr(ollama_config, "CONFIG_FILE", config_path)

    assert await ollama_config.load_persisted_config() == {}

    config_path.write_text("{invalid", encoding="utf-8")
    assert await ollama_config.load_persisted_config() == {}

    config_path.write_text("[]", encoding="utf-8")
    assert await ollama_config.load_persisted_config() == {}