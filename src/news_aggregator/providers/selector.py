"""Provider selection strategy."""

from typing import List

from ..config import ProviderConfig


class ProviderSelector:
    """Selects providers based on configured strategy."""

    def __init__(self, provider_configs: List[ProviderConfig], strategy: str = "priority"):
        """
        Initialize provider selector.

        Args:
            provider_configs: List of provider configurations
            strategy: Selection strategy ("priority", "cost", or "performance")
        """
        self.strategy = strategy
        self.provider_order = self._build_provider_order(provider_configs)

    def _build_provider_order(self, configs: List[ProviderConfig]) -> List[str]:
        """
        Build ordered list of provider IDs based on strategy.

        Args:
            configs: List of provider configurations

        Returns:
            Ordered list of provider IDs
        """
        # Filter to enabled providers only
        enabled_configs = [c for c in configs if c.enabled]

        if self.strategy == "priority":
            # Sort by priority field (lower number = higher priority)
            enabled_configs.sort(key=lambda c: c.priority)
        elif self.strategy == "cost":
            # Sort by estimated cost (cheapest first)
            enabled_configs.sort(key=lambda c: c.estimated_cost_per_request())
        elif self.strategy == "performance":
            # Sort by historical average latency (fastest first)
            # For now, same as priority since we don't have historical data
            enabled_configs.sort(key=lambda c: c.priority)
        else:
            # Default to priority if unknown strategy
            enabled_configs.sort(key=lambda c: c.priority)

        return [c.provider_id for c in enabled_configs]

    def get_provider_chain(self, article=None) -> List[str]:
        """
        Return ordered list of provider IDs to try for this article.

        Args:
            article: Article object (currently unused, reserved for future topic-based routing)

        Returns:
            Ordered list of provider IDs (copy to avoid mutation)
        """
        # For now, same chain for all articles
        # Future enhancement: topic-specific routing based on article.topic
        return self.provider_order.copy()
