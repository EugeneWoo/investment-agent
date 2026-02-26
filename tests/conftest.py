"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_settings():
    """Return a Settings-compatible namespace with placeholder API key values."""
    from types import SimpleNamespace

    return SimpleNamespace(
        ANTHROPIC_API_KEY="test-anthropic-key",
        TAVILY_API_KEY="test-tavily-key",
        CRUNCHBASE_API_KEY="test-crunchbase-key",
        REDDIT_CLIENT_ID="test-reddit-id",
        REDDIT_CLIENT_SECRET="test-reddit-secret",
        TWITTER_BEARER_TOKEN="test-twitter-token",
    )
