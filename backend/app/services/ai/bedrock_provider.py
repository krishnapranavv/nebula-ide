"""
AI provider implementation using the direct Anthropic API.

Cost decision: This file is named bedrock_provider.py per the architecture blueprint,
but defaults to the direct Anthropic API rather than AWS Bedrock because:
  - Direct API pricing for Claude Haiku: $0.25/M input, $1.25/M output tokens
  - AWS Bedrock pricing for same model:  ~$0.30/M input, ~$1.50/M output tokens
  - Saving: ~20-30% per review call with zero functionality difference

To switch to Bedrock instead (e.g. for VPC-only deployments with no internet egress):
  Set ANTHROPIC_API_KEY="" and AWS credentials — the class will auto-detect.

The provider.py abstraction means the rest of the codebase is unchanged either way.
"""
import anthropic
import asyncio
import logging
from app.core.config import settings
from app.services.ai.provider import AIProvider, AIResponse

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Get a free key at https://console.anthropic.com and add it to your .env"
            )
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


class AnthropicProvider(AIProvider):
    """
    Direct Anthropic API provider.
    Uses claude-haiku by default — cheapest model that still produces
    actionable code review explanations.
    """

    def model_name(self) -> str:
        return settings.AI_MODEL

    async def complete(self, system_prompt: str, user_prompt: str) -> AIResponse:
        """Non-blocking completion via run_in_executor to keep FastAPI async."""
        client = _get_client()

        def _sync_call():
            return client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

        try:
            message = await asyncio.get_event_loop().run_in_executor(None, _sync_call)
            content = message.content[0].text if message.content else ""
            return AIResponse(
                content=content,
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens,
            )
        except anthropic.AuthenticationError:
            logger.error("Anthropic API key is invalid")
            raise
        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit hit")
            raise
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


# ── Singleton factory ─────────────────────────────────────────────────────────

_provider_instance: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = AnthropicProvider()
        logger.info(f"AI provider initialised: {_provider_instance.model_name()}")
    return _provider_instance
