"""Provider registry for managing AI provider instances."""

from typing import Dict, List, Tuple

from ..config import ProviderConfig
from ..logger import get_logger
from .base import AIProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider


class ProviderRegistry:
    """Manages provider instances and lifecycle."""

    def __init__(self, provider_configs: List[ProviderConfig]):
        """
        Initialize provider registry.

        Args:
            provider_configs: List of provider configurations
        """
        self.providers: Dict[str, AIProvider] = {}
        self.logger = get_logger()
        self._initialize_providers(provider_configs)

    def _initialize_providers(self, configs: List[ProviderConfig]):
        """
        Create provider instances from configuration.

        Args:
            configs: List of provider configurations

        Raises:
            ValueError: If provider type is unknown
        """
        for config in configs:
            if not config.enabled:
                self.logger.info(f"Skipping disabled provider: {config.provider_id}")
                continue

            if config.provider_type == "anthropic":
                provider = AnthropicProvider(config.provider_id, config)
            elif config.provider_type == "openai":
                provider = OpenAIProvider(config.provider_id, config)
            else:
                raise ValueError(f"Unknown provider type: {config.provider_type}")

            self.providers[config.provider_id] = provider
            self.logger.info(
                f"Initialized provider: {config.provider_id} "
                f"({config.provider_type}, model: {config.model})"
            )

    def get_provider(self, provider_id: str) -> AIProvider:
        """
        Retrieve provider by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not found
        """
        if provider_id not in self.providers:
            raise ValueError(f"Provider not found: {provider_id}")
        return self.providers[provider_id]

    def get_all_providers(self) -> Dict[str, AIProvider]:
        """
        Return all registered providers.

        Returns:
            Dictionary mapping provider IDs to provider instances
        """
        return self.providers

    async def validate_all(self) -> Dict[str, Tuple[bool, str]]:
        """
        Test connectivity for all providers.

        Returns:
            Dictionary mapping provider IDs to (is_healthy, error_message) tuples
        """
        results = {}
        for provider_id, provider in self.providers.items():
            self.logger.info(f"Validating provider: {provider_id}")
            is_healthy, error = await provider.validate_connection()
            results[provider_id] = (is_healthy, error)

            if is_healthy:
                self.logger.info(f"Provider {provider_id} is healthy")
            else:
                self.logger.warning(f"Provider {provider_id} validation failed: {error}")

        return results
