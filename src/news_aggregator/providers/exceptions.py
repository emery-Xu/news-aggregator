"""Custom exceptions for AI provider operations."""


class ProviderAPIError(Exception):
    """Raised when a provider API call fails."""
    pass


class ProviderConfigError(Exception):
    """Raised when provider configuration is invalid."""
    pass
