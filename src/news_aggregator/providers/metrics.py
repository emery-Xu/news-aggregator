"""Provider metrics tracking."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ProviderMetrics:
    """Tracks usage statistics for a provider."""
    provider_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_seconds: float = 0.0
    consecutive_failures: int = 0

    def record_success(self, latency: float, input_tokens: int, output_tokens: int):
        """Record a successful API call."""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_latency_seconds += latency
        self.consecutive_failures = 0

    def record_failure(self, error: str):
        """Record a failed API call."""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1

    def average_latency(self) -> float:
        """Calculate average latency per successful request."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_seconds / self.successful_requests

    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for serialization."""
        return {
            "provider_id": self.provider_id,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate(),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "average_latency_seconds": self.average_latency()
        }
