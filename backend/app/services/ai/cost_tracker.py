"""
AI cost tracker.
Logs token usage per review and calculates estimated API costs.
Helps monitor spend against the $200 student budget.

Pricing (as of mid-2025, direct Anthropic API):
  claude-haiku-4-5:  $0.25/M input tokens, $1.25/M output tokens
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict

logger = logging.getLogger(__name__)

# Cost per 1M tokens (USD)
COST_RATES: Dict[str, Dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.25,  "output": 1.25},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "default":                   {"input": 0.25,  "output": 1.25},
}


@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_RATES.get(model, COST_RATES["default"])
    return (input_tokens / 1_000_000 * rates["input"]) + (output_tokens / 1_000_000 * rates["output"])


def log_usage(model: str, input_tokens: int, output_tokens: int) -> UsageRecord:
    cost = calculate_cost(model, input_tokens, output_tokens)
    record = UsageRecord(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )
    logger.info(
        f"AI usage — model={model} "
        f"in={input_tokens} out={output_tokens} "
        f"cost=${cost:.6f}"
    )
    return record
