"""
Authentication service — business logic for signup, login, token refresh.
Separated from the route layer so it's independently testable.
"""
from fastapi import HTTPException
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.database import db_create_user, db_get_user_by_email, db_get_user_by_id, db_update_last_login
import logging

logger = logging.getLogger(__name__)


async def signup(email: str, username: str, password: str) -> dict:
    existing = await db_get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await db_create_user(email, username, hash_password(password))
    logger.info(f"New user registered: {user['user_id']} ({email})")
    return _token_payload(user)


async def login(email: str, password: str) -> dict:
    user = await db_get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db_update_last_login(user["user_id"])
    logger.info(f"User logged in: {user['user_id']}")
    return _token_payload(user)


async def refresh(refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user = await db_get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return _token_payload(user)


def _token_payload(user: dict) -> dict:
    return {
        "access_token":  create_access_token(user["user_id"], user["role"]),
        "refresh_token": create_refresh_token(user["user_id"]),
        "user_id":       user["user_id"],
        "username":      user["username"],
        "role":          user["role"],
    }
