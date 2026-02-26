"""Tests for Tavily web search client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tools.tavily import TavilyClient


@patch("tools.tavily.TavilySDKClient")
def test_search_returns_results(mock_cls, mock_settings):
    mock_instance = MagicMock()
    mock_instance.search.return_value = {
        "results": [{"title": "Result", "url": "https://example.com", "content": "Content", "score": 0.9}]
    }
    mock_cls.return_value = mock_instance

    with patch("tools.tavily.settings", mock_settings):
        client = TavilyClient()
        results = client.search("test query")

    assert len(results) == 1
    assert results[0]["title"] == "Result"
    assert mock_instance.search.call_count == 1


@patch("tools.tavily.TavilySDKClient")
def test_search_caches_results(mock_cls, mock_settings):
    mock_instance = MagicMock()
    mock_instance.search.return_value = {"results": []}
    mock_cls.return_value = mock_instance

    with patch("tools.tavily.settings", mock_settings):
        client = TavilyClient()
        client.search("test query")
        client.search("test query")

    assert mock_instance.search.call_count == 1  # second call hits cache


@patch("tools.tavily.TavilySDKClient")
def test_search_failure_returns_empty_list(mock_cls, mock_settings):
    mock_instance = MagicMock()
    mock_instance.search.side_effect = Exception("API error")
    mock_cls.return_value = mock_instance

    with patch("tools.tavily.settings", mock_settings):
        client = TavilyClient()
        results = client.search("test query")

    assert results == []
