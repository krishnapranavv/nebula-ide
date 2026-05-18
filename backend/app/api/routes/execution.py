from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import ExecuteRequest, ExecutionResponse
from app.services.execution.executor import run_code
from app.core.security import get_current_user
from app.core.database import db_save_execution, db_list_executions
from app.core.rate_limiter import limiter
from app.core.config import settings
from datetime import datetime, timezone
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ExecutionResponse)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
async def execute_code(body: ExecuteRequest, request=None, user: dict = Depends(get_current_user)):
    logger.info(f"Execution request: user={user['user_id']} lang={body.language}")

    result = await run_code(body.code, body.language, body.stdin)

    # Persist execution record
    exec_record = {
        "exec_id":     result.exec_id,
        "user_id":     user["user_id"],
        "language":    body.language,
        "stdout":      result.stdout,
        "stderr":      result.stderr,
        "exit_code":   result.exit_code,
        "runtime_ms":  result.runtime_ms,
        "timed_out":   result.timed_out,
        "executed_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if body.project_id:
        exec_record["project_id"] = body.project_id
    if body.file_id:
        exec_record["file_id"] = body.file_id

    await db_save_execution(exec_record)

    return ExecutionResponse(**exec_record)


@router.get("/history")
async def execution_history(user: dict = Depends(get_current_user)):
    records = await db_list_executions(user["user_id"])
    return {"executions": records}
