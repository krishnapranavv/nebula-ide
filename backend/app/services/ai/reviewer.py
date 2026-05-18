"""
Code review orchestrator.

Pipeline:
  1. Static analysis  → deterministic findings (free, fast)
  2. Triage filter    → deduplicate, sort by severity, cap at N
  3. AI explanation   → WHY + corrected implementation (costs tokens)
  4. Merge            → unify static + AI findings into ReviewResult
  5. Persist          → save to DynamoDB for history

Cost controls:
  - Per-user daily review quota (AI_DAILY_REVIEW_LIMIT)
  - Finding cap before sending to AI (AI_MAX_FINDINGS_PER_REVIEW)
  - Code line cap (AI_MAX_CODE_LINES)
  - Cache by code hash: identical code → no API call
"""
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import List

from app.core.config import settings
from app.core.database import db_save_review, db_get_daily_review_count
from app.models.models import ReviewResult, Finding
from app.services.ai.static_analysis import analyse, RawFinding
from app.services.ai.bedrock_provider import get_ai_provider
from app.services.ai.prompt_builder import build_review_prompt, SYSTEM_PROMPT
from app.services.ai.cost_tracker import log_usage
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# In-memory review cache keyed by (language, code_hash)
# Resets on restart — enough for dev/demo, prevents repeat costs
_review_cache: dict[str, dict] = {}


def _code_hash(code: str, language: str) -> str:
    return hashlib.sha256(f"{language}:{code}".encode()).hexdigest()[:16]


async def review_code(
    user_id: str,
    code: str,
    language: str,
    project_id: str | None = None,
    file_id: str | None = None,
) -> ReviewResult:
    # ── 1. Daily quota enforcement ────────────────────────────────────────────
    daily_count = await db_get_daily_review_count(user_id)
    if daily_count >= settings.AI_DAILY_REVIEW_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily review limit ({settings.AI_DAILY_REVIEW_LIMIT}) reached. Try again tomorrow.",
        )

    # ── 2. Cache check ────────────────────────────────────────────────────────
    cache_key = _code_hash(code, language)
    if cache_key in _review_cache:
        logger.info(f"Cache hit for review {cache_key} — skipping AI call")
        cached = _review_cache[cache_key]
        # Return with fresh review_id so it persists as a new record
        result = ReviewResult(**{**cached, "review_id": str(uuid.uuid4()), "user_id": user_id})
        await _persist(result, project_id, file_id)
        return result

    # ── 3. Static analysis ────────────────────────────────────────────────────
    raw_findings: List[RawFinding] = analyse(code, language)
    logger.info(f"Static analysis: {len(raw_findings)} findings for {language}")

    # ── 4. AI explanation ─────────────────────────────────────────────────────
    provider = get_ai_provider()
    user_prompt = build_review_prompt(code, language, raw_findings)

    try:
        response = await provider.complete(SYSTEM_PROMPT, user_prompt)
        usage = log_usage(provider.model_name(), response.input_tokens, response.output_tokens)
    except Exception as e:
        logger.error(f"AI provider error: {e}")
        # Graceful degradation — return static analysis only
        return _static_only_result(user_id, language, raw_findings, project_id, file_id)

    # ── 5. Parse AI response ──────────────────────────────────────────────────
    try:
        cleaned = response.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        ai_data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"AI response JSON parse failed: {e} — falling back to static only")
        return _static_only_result(user_id, language, raw_findings, project_id, file_id)

    # ── 6. Build unified findings ─────────────────────────────────────────────
    ai_findings: List[Finding] = []
    for item in ai_data.get("findings", []):
        ai_findings.append(Finding(
            line=item.get("line", 1),
            severity=item.get("severity", "warning"),
            category=item.get("category", "other"),
            rule_id=item.get("rule_id", "ai-review"),
            message=item.get("message", ""),
            explanation=item.get("explanation", ""),
            fix=item.get("fix"),
            source="ai",
        ))

    result = ReviewResult(
        review_id=str(uuid.uuid4()),
        user_id=user_id,
        language=language,
        overall_score=max(1, min(10, ai_data.get("overall_score", 5))),
        summary=ai_data.get("summary", "Review complete."),
        findings=ai_findings,
        model_used=provider.model_name(),
        tokens_used=response.total_tokens,
        reviewed_at=datetime.now(tz=timezone.utc).isoformat(),
    )

    # Cache result (without user_id to make it user-agnostic)
    _review_cache[cache_key] = {
        "language": result.language,
        "overall_score": result.overall_score,
        "summary": result.summary,
        "findings": result.findings,
        "model_used": result.model_used,
        "tokens_used": result.tokens_used,
        "reviewed_at": result.reviewed_at,
    }

    await _persist(result, project_id, file_id)
    return result


def _static_only_result(
    user_id: str, language: str, raw: List[RawFinding],
    project_id=None, file_id=None
) -> ReviewResult:
    """Fallback when AI provider is unavailable — static analysis findings only."""
    findings = [
        Finding(
            line=f.line, severity=f.severity, category=f.category,
            rule_id=f.rule_id, message=f.message,
            explanation=f"Detected by {f.tool}. Check documentation for rule {f.rule_id}.",
            fix=None, source="static",
        )
        for f in raw[:settings.AI_MAX_FINDINGS_PER_REVIEW]
    ]
    return ReviewResult(
        review_id=str(uuid.uuid4()),
        user_id=user_id,
        language=language,
        overall_score=max(1, 10 - len([f for f in findings if f.severity == "error"]) * 2),
        summary=f"Static analysis found {len(findings)} issue(s). AI explanation unavailable.",
        findings=findings,
        model_used="static-analysis-only",
        tokens_used=0,
        reviewed_at=datetime.now(tz=timezone.utc).isoformat(),
    )


async def _persist(result: ReviewResult, project_id=None, file_id=None):
    import dataclasses
    data = dataclasses.asdict(result)
    if project_id:
        data["project_id"] = project_id
    if file_id:
        data["file_id"] = file_id
    await db_save_review(data)
