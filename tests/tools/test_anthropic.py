"""Tests for Anthropic Claude LLM client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.anthropic import AnthropicClient


@patch("tools.anthropic.Anthropic")
def test_messages_create_returns_text(mock_cls, mock_settings):
    mock_block = MagicMock()
    mock_block.text = "Hello from Claude"
    mock_instance = MagicMock()
    mock_instance.messages.create.return_value = MagicMock(content=[mock_block])
    mock_cls.return_value = mock_instance

    with patch("tools.anthropic.settings", mock_settings):
        client = AnthropicClient()
        result = client.messages_create("system", "user message")

    assert result == "Hello from Claude"


@patch("tools.anthropic.Anthropic")
def test_messages_create_raises_on_failure(mock_cls, mock_settings):
    mock_instance = MagicMock()
    mock_instance.messages.create.side_effect = Exception("rate limit")
    mock_cls.return_value = mock_instance

    with patch("tools.anthropic.settings", mock_settings):
        client = AnthropicClient()
        with pytest.raises(RuntimeError):
            client.messages_create("system", "user message")
