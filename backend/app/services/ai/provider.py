"""
Abstract AI provider interface.
Decouples the reviewer from any specific AI backend.
Swap implementations by changing AI_PROVIDER in config.

Available providers:
  - "anthropic"  Direct Anthropic API  (~30% cheaper than Bedrock)
  - "bedrock"    AWS Bedrock           (useful if you need IAM-only auth)

Default is "anthropic" for cost efficiency.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class AIResponse:
    content: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class AIProvider(ABC):
    """Base class for all AI provider implementations."""

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> AIResponse:
        """Send a completion request and return the structured response."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string for logging/cost tracking."""
        ...
