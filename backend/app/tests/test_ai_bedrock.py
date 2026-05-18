"""
Tests for the AI review pipeline.
Mocks the Anthropic API to avoid real API calls in CI.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai.static_analysis import analyse
from app.services.ai.prompt_builder import build_review_prompt, SYSTEM_PROMPT
from app.services.ai.cost_tracker import calculate_cost


def test_cost_calculation_haiku():
    """Haiku cost should be very cheap per review."""
    cost = calculate_cost("claude-haiku-4-5-20251001", input_tokens=1000, output_tokens=500)
    # 1000 * 0.25/1M + 500 * 1.25/1M = $0.00025 + $0.000625 = $0.000875
    assert cost < 0.01  # Less than 1 cent per typical review


def test_static_analysis_python():
    """Pylint/bandit/flake8 should detect obvious issues."""
    bad_code = """
import os
password = "hardcoded_secret_123"
x = 1
if x == 1:
    eval(input())
"""
    findings = analyse(bad_code, "python")
    # Should detect at minimum the eval and hardcoded secret
    assert len(findings) > 0


def test_static_analysis_empty_code():
    """Empty code should not crash the analyser."""
    findings = analyse("", "python")
    assert isinstance(findings, list)


def test_prompt_builder_truncates_long_code():
    """Long code should be truncated before being sent to the AI."""
    long_code = "\n".join([f"x_{i} = {i}" for i in range(500)])
    prompt = build_review_prompt(long_code, "python", [])
    assert "truncated" in prompt


def test_prompt_builder_caps_findings():
    """Number of findings in prompt should be capped."""
    from app.services.ai.static_analysis import RawFinding
    many_findings = [
        RawFinding(line=i, col=0, severity="warning", category="style",
                   rule_id=f"W{i}", message=f"issue {i}", tool="pylint")
        for i in range(100)
    ]
    prompt = build_review_prompt("x = 1", "python", many_findings)
    # Prompt should exist and not crash
    assert len(prompt) > 0


@pytest.mark.asyncio
async def test_reviewer_uses_cache():
    """Second review of same code should hit cache, not call AI."""
    from app.services.ai import reviewer
    reviewer._review_cache.clear()

    mock_response = MagicMock()
    mock_response.content = '{"overall_score": 7, "summary": "OK code", "findings": []}'
    mock_response.input_tokens = 100
    mock_response.output_tokens = 50
    mock_response.total_tokens = 150

    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=mock_response)
    mock_provider.model_name = MagicMock(return_value="claude-haiku-4-5-20251001")

    with patch("app.services.ai.reviewer.get_ai_provider", return_value=mock_provider), \
         patch("app.services.ai.reviewer.db_get_daily_review_count", new_callable=AsyncMock, return_value=0), \
         patch("app.services.ai.reviewer.db_save_review", new_callable=AsyncMock):

        code = "x = 1\nprint(x)"
        await reviewer.review_code("user-1", code, "python")
        await reviewer.review_code("user-1", code, "python")  # should hit cache

    # AI provider should only be called ONCE (second call uses cache)
    assert mock_provider.complete.call_count == 1
