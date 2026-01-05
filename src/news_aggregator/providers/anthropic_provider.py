"""Anthropic Claude API provider implementation."""

import asyncio
import time
from typing import List, Dict, Tuple

from anthropic import AsyncAnthropic
from anthropic import RateLimitError, APIError

from ..config import ProviderConfig
from .base import AIProvider
from .exceptions import ProviderAPIError


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(self, provider_id: str, config: ProviderConfig):
        """
        Initialize Anthropic provider.

        Args:
            provider_id: Unique identifier for this provider
            config: Provider configuration
        """
        super().__init__(provider_id, config)

        # Initialize AsyncAnthropic client
        client_kwargs = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self.client = AsyncAnthropic(**client_kwargs)
        self.model = config.model
        self.timeout = config.timeout

    async def summarize_async(
        self,
        article,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Summarize article using Anthropic Claude API.

        Args:
            article: Article object to summarize
            prompt: Formatted prompt for Claude
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Tuple of (bullet_points, usage_dict)

        Raises:
            ProviderAPIError: If API call fails after retries
        """
        start_time = time.time()

        for attempt in range(3):  # Max 3 retries
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=self.timeout
                )

                # Extract text and parse bullets
                summary_text = response.content[0].text
                bullets = self._parse_bullets(summary_text)

                # Record metrics
                latency = time.time() - start_time
                self.metrics.record_success(
                    latency,
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )

                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }

                return bullets, usage

            except RateLimitError as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                if attempt < 2:
                    await asyncio.sleep(wait_time)
                else:
                    self.metrics.record_failure(str(e))
                    raise ProviderAPIError(f"Rate limit exceeded after {attempt + 1} attempts: {e}")

            except APIError as e:
                # Record failure and propagate
                self.metrics.record_failure(str(e))
                raise ProviderAPIError(f"Anthropic API error: {e}")

            except Exception as e:
                # Catch any other unexpected errors
                self.metrics.record_failure(str(e))
                raise ProviderAPIError(f"Unexpected error calling Anthropic API: {e}")

        # Should not reach here, but just in case
        raise ProviderAPIError("Failed to summarize after maximum retries")

    async def validate_connection(self) -> Tuple[bool, str]:
        """
        Test Anthropic API connectivity.

        Returns:
            Tuple of (is_healthy, error_message)
        """
        try:
            # Minimal test: simple echo request
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
                timeout=10  # Short timeout for health check
            )
            return True, ""
        except Exception as e:
            return False, str(e)
