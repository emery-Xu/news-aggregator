"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import re

from ..config import ProviderConfig
from .metrics import ProviderMetrics


class AIProvider(ABC):
    """Abstract base class for AI API providers."""

    def __init__(self, provider_id: str, config: ProviderConfig):
        """
        Initialize provider.

        Args:
            provider_id: Unique identifier for this provider instance
            config: Provider configuration
        """
        self.provider_id = provider_id
        self.config = config
        self.metrics = ProviderMetrics(provider_id)

    @abstractmethod
    async def summarize_async(
        self,
        article,  # Article type from models
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Summarize article using provider's API.

        Args:
            article: Article object to summarize
            prompt: Formatted prompt for the AI model
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Tuple of (bullet_points, usage_dict)
            usage_dict contains 'input_tokens' and 'output_tokens'

        Raises:
            ProviderAPIError: If API call fails
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> Tuple[bool, str]:
        """
        Test provider API connectivity.

        Returns:
            Tuple of (is_healthy, error_message)
            error_message is empty string if healthy
        """
        pass

    def get_usage_stats(self) -> Dict:
        """
        Return provider metrics.

        Returns:
            Dictionary with usage statistics
        """
        return self.metrics.to_dict()

    def _parse_bullets(self, summary_text: str) -> List[str]:
        """
        Parse bullet points from Claude's response.

        Args:
            summary_text: Raw summary text from AI model

        Returns:
            List of bullet point strings
        """
        bullets = []

        # Split by lines
        lines = summary_text.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove bullet characters and clean up
            # Support various bullet formats: •, -, *, 1., 2., etc.
            for bullet_char in ['•', '•', '-', '*', '→', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.']:
                if line.startswith(bullet_char):
                    line = line[len(bullet_char):].strip()
                    break

            # Also handle numbered lists like "1) " or "1: "
            line = re.sub(r'^\d+[\):\.]?\s+', '', line)

            # Skip very short lines (likely formatting artifacts)
            if len(line) < 10:
                continue

            bullets.append(line)

        return bullets
