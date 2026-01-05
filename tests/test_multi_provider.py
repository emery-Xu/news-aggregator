"""Tests for multi-provider system."""

import pytest
from pathlib import Path
from news_aggregator.config import ProviderConfig
from news_aggregator.providers import ProviderRegistry, ProviderSelector


def test_provider_config_creation():
    """Test ProviderConfig dataclass."""
    config = ProviderConfig(
        provider_id="test_anthropic",
        provider_type="anthropic",
        api_key="test-key",
        model="claude-sonnet-4-5",
        enabled=True,
        priority=1
    )
    assert config.provider_id == "test_anthropic"
    assert config.provider_type == "anthropic"
    assert config.priority == 1
    assert config.timeout == 30  # Default value


def test_provider_selector_priority_strategy():
    """Test provider selector with priority strategy."""
    configs = [
        ProviderConfig(
            provider_id="provider_low_priority",
            provider_type="anthropic",
            api_key="key1",
            model="claude-sonnet-4-5",
            priority=10
        ),
        ProviderConfig(
            provider_id="provider_high_priority",
            provider_type="openai",
            api_key="key2",
            model="gpt-4-turbo",
            priority=1
        )
    ]

    selector = ProviderSelector(configs, strategy="priority")
    chain = selector.get_provider_chain()

    # Should be ordered by priority (lower number = higher priority)
    assert chain[0] == "provider_high_priority"
    assert chain[1] == "provider_low_priority"


def test_provider_selector_cost_strategy():
    """Test provider selector with cost strategy."""
    configs = [
        ProviderConfig(
            provider_id="expensive",
            provider_type="anthropic",
            api_key="key1",
            model="claude-sonnet-4-5",
            priority=1,
            input_cost_per_1M_tokens=10.0,
            output_cost_per_1M_tokens=30.0
        ),
        ProviderConfig(
            provider_id="cheap",
            provider_type="openai",
            api_key="key2",
            model="gpt-3.5-turbo",
            priority=2,
            input_cost_per_1M_tokens=0.5,
            output_cost_per_1M_tokens=1.5
        )
    ]

    selector = ProviderSelector(configs, strategy="cost")
    chain = selector.get_provider_chain()

    # Should be ordered by cost (cheapest first)
    assert chain[0] == "cheap"
    assert chain[1] == "expensive"


def test_provider_selector_disabled_providers():
    """Test that disabled providers are excluded."""
    configs = [
        ProviderConfig(
            provider_id="enabled",
            provider_type="anthropic",
            api_key="key1",
            model="claude-sonnet-4-5",
            enabled=True,
            priority=1
        ),
        ProviderConfig(
            provider_id="disabled",
            provider_type="openai",
            api_key="key2",
            model="gpt-4",
            enabled=False,
            priority=2
        )
    ]

    selector = ProviderSelector(configs, strategy="priority")
    chain = selector.get_provider_chain()

    # Only enabled provider should be in chain
    assert len(chain) == 1
    assert chain[0] == "enabled"


def test_provider_cost_estimation():
    """Test cost estimation method."""
    config = ProviderConfig(
        provider_id="test",
        provider_type="anthropic",
        api_key="key",
        model="claude-sonnet-4-5",
        input_cost_per_1M_tokens=3.0,
        output_cost_per_1M_tokens=15.0
    )

    # Estimate cost for 1000 input tokens and 200 output tokens
    cost = config.estimated_cost_per_request(avg_input_tokens=1000, avg_output_tokens=200)

    expected_input_cost = (1000 / 1_000_000) * 3.0  # 0.003
    expected_output_cost = (200 / 1_000_000) * 15.0  # 0.003
    expected_total = expected_input_cost + expected_output_cost  # 0.006

    assert abs(cost - expected_total) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
