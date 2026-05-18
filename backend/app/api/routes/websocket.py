"""
WebSocket endpoint for real-time execution output streaming.
Phase 4 feature — foundation is wired up, streaming logic added here.

Architecture note: For Phase 1-3, the REST /execute endpoint is sufficient.
WebSocket is wired at startup so the frontend can enable it later without
any backend restructuring.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_token
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/execute")
async def ws_execute(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket execution endpoint.
    Authentication via token query param (standard WS auth pattern).
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    logger.info(f"WebSocket connected: user={user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            code = data.get("code", "")
            language = data.get("language", "python")
            stdin = data.get("stdin", "")

            await websocket.send_json({"type": "status", "message": "Running..."})

            # Import here to avoid circular dependency at module level
            from app.services.execution.executor import run_code
            result = await run_code(code, language, stdin)

            await websocket.send_json({
                "type":       "result",
                "exec_id":    result.exec_id,
                "stdout":     result.stdout,
                "stderr":     result.stderr,
                "exit_code":  result.exit_code,
                "runtime_ms": result.runtime_ms,
                "timed_out":  result.timed_out,
            })
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user={user_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
