"""
Nebula IDE — FastAPI application entry point.
Wires together all routers, middleware, and startup events.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_tables
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.api.routes import auth, execution, health, projects, review, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_tables()
    from app.services.storage.s3 import ensure_bucket
    await ensure_bucket()
    import logging
    logging.getLogger(__name__).info("Nebula IDE API ready.")
    yield


app = FastAPI(
    title="Nebula IDE API",
    description="AI-powered cloud IDE with secure sandboxed execution",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# ── Rate limiter ───────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Global error handler ───────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger(__name__).error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router,    prefix="/api/health",    tags=["health"])
app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(execution.router, prefix="/api/execute",   tags=["execution"])
app.include_router(projects.router,  prefix="/api/projects",  tags=["projects"])
app.include_router(review.router,    prefix="/api/review",    tags=["review"])
app.include_router(websocket.router, tags=["websocket"])
