"""Tavily web search client with caching and retry logic."""

from __future__ import annotations

import hashlib
import logging
from typing import TypedDict

from tavily import TavilyClient as TavilySDKClient
from tavily.errors import BadRequestError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class TavilySearchResult(TypedDict):
    """Structured result from Tavily search API."""

    title: str
    url: str
    content: str
    score: float | None


class TavilyClient:
    """Tavily web search client with in-memory caching and retry logic.

    On API failures, returns empty list and logs warning (never raises).
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Tavily client with API key.

        Args:
            api_key: Tavily API key. If None, loads from settings.
        """
        self.api_key = api_key or settings.TAVILY_API_KEY
        self._client = TavilySDKClient(api_key=self.api_key)
        self._cache: dict[str, list[TavilySearchResult]] = {}

    def _hash_query(self, query: str) -> str:
        """Generate SHA256 hash for query cache key.

        Args:
            query: Search query string.

        Returns:
            Hexadecimal hash string.
        """
        return hashlib.sha256(query.encode()).hexdigest()

    @retry(
        retry=retry_if_exception_type((BadRequestError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _search_with_retry(
        self, query: str, max_results: int
    ) -> list[TavilySearchResult]:
        """Execute Tavily search with retry logic.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of TavilySearchResult dictionaries.

        Raises:
            BadRequestError: If API fails after retries.
            OSError: If network fails after retries.
        """
        response = self._client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
            include_raw_content=False,
        )

        results: list[TavilySearchResult] = []
        for item in response.get("results", []):
            results.append(
                TavilySearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score"),
                )
            )

        return results

    def search(self, query: str, max_results: int = 10) -> list[TavilySearchResult]:
        """Search the web using Tavily API with caching.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return (default: 10).

        Returns:
            List of TavilySearchResult dictionaries. Returns empty list on API failure.
        """
        cache_key = self._hash_query(query)

        # Check cache
        if cache_key in self._cache:
            logger.debug(f"Cache hit for query: {query}")
            return self._cache[cache_key]

        # Execute search with error handling
        try:
            results = self._search_with_retry(query, max_results)
            self._cache[cache_key] = results
            logger.info(
                f"Tavily search successful: {len(results)} results for query: {query}"
            )
            return results
        except Exception as e:
            logger.warning(f"Tavily search failed for query '{query}': {e}")
            return []

    def clear_cache(self) -> None:
        """Clear the in-memory search cache.

        Useful for testing to ensure fresh results.
        """
        self._cache.clear()
        logger.debug("Tavily search cache cleared")
