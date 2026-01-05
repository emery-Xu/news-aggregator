"""OpenAI API provider implementation."""

import asyncio
import time
from typing import List, Dict, Tuple

from openai import AsyncOpenAI
from openai import RateLimitError, APIError

from ..config import ProviderConfig
from .base import AIProvider
from .exceptions import ProviderAPIError


class OpenAIProvider(AIProvider):
    """OpenAI API provider (supports OpenAI and Azure endpoints)."""

    def __init__(self, provider_id: str, config: ProviderConfig):
        """
        Initialize OpenAI provider.

        Args:
            provider_id: Unique identifier for this provider
            config: Provider configuration
        """
        super().__init__(provider_id, config)

        # Initialize AsyncOpenAI client
        client_kwargs = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self.client = AsyncOpenAI(**client_kwargs)
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
        Summarize article using OpenAI API.

        Args:
            article: Article object to summarize
            prompt: Formatted prompt for GPT
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
                # Convert single prompt to chat format
                messages = [
                    {"role": "system", "content": "You are a helpful assistant that summarizes articles."},
                    {"role": "user", "content": prompt}
                ]

                response = await self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    timeout=self.timeout
                )

                # Extract text and parse bullets
                summary_text = response.choices[0].message.content
                bullets = self._parse_bullets(summary_text)

                # Record metrics
                latency = time.time() - start_time
                self.metrics.record_success(
                    latency,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )

                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
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
                raise ProviderAPIError(f"OpenAI API error: {e}")

            except Exception as e:
                # Catch any other unexpected errors
                self.metrics.record_failure(str(e))
                raise ProviderAPIError(f"Unexpected error calling OpenAI API: {e}")

        # Should not reach here, but just in case
        raise ProviderAPIError("Failed to summarize after maximum retries")

    async def validate_connection(self) -> Tuple[bool, str]:
        """
        Test OpenAI API connectivity.

        Returns:
            Tuple of (is_healthy, error_message)
        """
        try:
            # Minimal test: simple echo request
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
                timeout=10  # Short timeout for health check
            )
            return True, ""
        except Exception as e:
            return False, str(e)
