"""Application configuration using pydantic-settings.

All API keys are read from environment variables / .env file.
Services gracefully degrade when keys are missing (mock data / placeholders).
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "OffroadTrip"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://offroadtrip:password@postgres:5432/offroadtrip"
    # SQLite fallback for local dev without Docker
    DATABASE_URL_DEV: str = "sqlite:///./offroadtrip.db"

    # ── LLM via silk-gateway (OpenAI-compatible) ──────────────────────────
    # Your own Cloudflare Workers gateway supporting DeepSeek / Doubao / Kimi
    SILK_GATEWAY_URL: str = ""
    SILK_GATEWAY_KEY: str = ""
    # Default model for route planning (cheap & capable)
    LLM_MODEL: str = "deepseek-chat"
    # Stronger model for content enrichment (scenic/food/history)
    LLM_MODEL_STRONG: str = "deepseek-chat"
    LLM_TIMEOUT: int = 120
    LLM_TEMPERATURE: float = 0.8

    # ── Tencent Maps (腾讯位置服务) ────────────────────────────────────────
    # One key works for both WebService (backend) and JS API GL (frontend).
    # Recommend: use a backend key (IP whitelist / SN) + a frontend key (domain whitelist).
    QQ_MAP_KEY: str = ""  # backend WebService key
    QQ_MAP_JS_KEY: str = ""  # frontend JS API GL key (falls back to QQ_MAP_KEY)

    # ── Weather (和风天气, optimized for China) ───────────────────────────
    QWEATHER_KEY: str = ""
    QWEATHER_BASE_URL: str = "https://devapi.qweather.com"

    # ── Unsplash (scenic / food photos) ───────────────────────────────────
    UNSPLASH_ACCESS_KEY: str = ""

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def use_sqlite(self) -> bool:
        """Use SQLite when PostgreSQL isn't available (local dev)."""
        return self.DATABASE_URL.startswith("sqlite")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
