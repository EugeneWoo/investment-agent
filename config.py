"""Config module for secrets loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Application settings with required API keys."""

    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: str
    CRUNCHBASE_API_KEY: str
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    TWITTER_BEARER_TOKEN: str


REQUIRED_KEYS = [
    "ANTHROPIC_API_KEY",
    "TAVILY_API_KEY",
]

OPTIONAL_KEYS = [
    "CRUNCHBASE_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "TWITTER_BEARER_TOKEN",
]


def load_secrets() -> Settings:
    """Load secrets from Streamlit Cloud or local environment.

    Fallback chain:
    1. st.secrets[key] (Streamlit Cloud)
    2. os.environ[key] (local dev, populated by .env via load_dotenv)
    3. RuntimeError if key missing from all sources

    Returns:
        Settings: Validated settings with all required keys

    Raises:
        RuntimeError: If any required key is missing
    """
    # Try importing streamlit for cloud secrets; fall back gracefully if not available
    try:
        import streamlit as st

        has_streamlit = True
    except Exception:
        has_streamlit = False

    # Load .env file for local development
    load_dotenv()

    resolved_keys: dict[str, str] = {}

    def _resolve(key: str) -> str | None:
        if has_streamlit:
            try:
                return st.secrets[key]  # type: ignore[return-value]
            except (FileNotFoundError, KeyError):
                pass
        return os.environ.get(key)

    for key in REQUIRED_KEYS:
        value = _resolve(key)
        if not value:
            raise RuntimeError(f"Missing required secret: {key}")
        resolved_keys[key] = value

    for key in OPTIONAL_KEYS:
        resolved_keys[key] = _resolve(key) or ""

    return Settings(**resolved_keys)


# Module-level singleton - executes at import time
settings: Settings = load_secrets()
