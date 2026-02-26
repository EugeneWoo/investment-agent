"""Anthropic Claude LLM client with retry logic."""

from __future__ import annotations

import logging

from anthropic import Anthropic
from anthropic.types import Message
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Anthropic Claude LLM client wrapper with retry logic.

    On API failures, logs error and re-raises with context (LLM calls are critical).
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Anthropic client with API key.

        Args:
            api_key: Anthropic API key. If None, loads from settings.
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._client = Anthropic(api_key=self.api_key)
        self._model = "claude-sonnet-4-6"

    @retry(
        retry=retry_if_exception_type(
            (
                Exception,  # Anthropic can raise various exceptions
            )
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _create_with_retry(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
    ) -> Message:
        """Execute Anthropic API call with retry logic.

        Args:
            system_prompt: System prompt for the LLM.
            user_message: User message content.
            max_tokens: Maximum tokens in response.

        Returns:
            Anthropic Message object.

        Raises:
            Exception: If API fails after retries (various Anthropic exceptions).
        """
        return self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message},
            ],
        )

    def messages_create(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response from Claude using the Anthropic API.

        Args:
            system_prompt: System prompt for the LLM.
            user_message: User message content.
            max_tokens: Maximum tokens in response (default: 4096).

        Returns:
            Response text content from Claude.

        Raises:
            Exception: If API fails after retries, with additional context logged.
        """
        try:
            response = self._create_with_retry(system_prompt, user_message, max_tokens)

            # Extract first text block from response
            text_blocks = [b for b in response.content if hasattr(b, "text")]
            if text_blocks:
                text_content = text_blocks[0].text
                logger.info(f"Anthropic API call successful: {len(text_content)} chars")
                return text_content
            else:
                logger.warning("Anthropic API returned empty content")
                return ""

        except Exception as e:
            error_msg = (
                f"Anthropic API call failed for message"
                f" (first 100 chars): '{user_message[:100]}...': {e}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
