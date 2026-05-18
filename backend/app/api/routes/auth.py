from fastapi import APIRouter, Depends
from app.models.schemas import SignupRequest, LoginRequest, RefreshRequest, TokenResponse, MeResponse, MessageResponse
from app.services.auth.auth_service import signup, login, refresh
from app.core.security import get_current_user
from app.core.rate_limiter import limiter
from app.core.config import settings

router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=201)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def signup_route(body: SignupRequest, request=None):
    return await signup(body.email, body.username, body.password)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login_route(body: LoginRequest, request=None):
    return await login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_route(body: RefreshRequest):
    return await refresh(body.refresh_token)


@router.get("/me", response_model=MeResponse)
async def me_route(user: dict = Depends(get_current_user)):
    return {
        "user_id":    user["user_id"],
        "email":      user["email"],
        "username":   user["username"],
        "role":       user["role"],
        "created_at": user["created_at"],
    }
