from fastapi import APIRouter, Depends
from app.models.schemas import ReviewRequest, ReviewResponse, FindingSchema
from app.services.ai.reviewer import review_code
from app.core.security import get_current_user
from app.core.rate_limiter import limiter
from app.core.config import settings
import dataclasses
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ReviewResponse)
@limiter.limit(settings.RATE_LIMIT_REVIEW)
async def review(body: ReviewRequest, request=None, user: dict = Depends(get_current_user)):
    logger.info(f"Review request: user={user['user_id']} lang={body.language}")
    result = await review_code(
        user_id=user["user_id"],
        code=body.code,
        language=body.language,
        project_id=body.project_id,
        file_id=body.file_id,
    )
    return ReviewResponse(
        review_id=result.review_id,
        overall_score=result.overall_score,
        summary=result.summary,
        findings=[FindingSchema(**dataclasses.asdict(f)) for f in result.findings],
        model_used=result.model_used,
        tokens_used=result.tokens_used,
        reviewed_at=result.reviewed_at,
        language=result.language,
    )
