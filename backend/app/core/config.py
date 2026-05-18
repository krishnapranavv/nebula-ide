"""
Central configuration via pydantic-settings.
All secrets come from environment variables / AWS SSM — never hardcoded.
Cost-optimised defaults: Haiku model, tight token limits, DynamoDB free tier.
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "Nebula IDE"
    ENVIRONMENT: str = "development"      # development | production
    DEBUG: bool = True
    VERSION: str = "1.0.0"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-change-in-production-use-ssm"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # ── AWS ───────────────────────────────────────────────────────────────────
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # ── DynamoDB (free tier: 25 RCU / 25 WCU) ────────────────────────────────
    DYNAMODB_ENDPOINT_URL: str = ""       # http://localhost:8000 for local dev
    TABLE_USERS: str = "nebula_users"
    TABLE_PROJECTS: str = "nebula_projects"
    TABLE_FILES: str = "nebula_files"
    TABLE_EXECUTIONS: str = "nebula_executions"
    TABLE_REVIEWS: str = "nebula_reviews"

    # ── S3 ────────────────────────────────────────────────────────────────────
    S3_ENDPOINT_URL: str = ""             # http://localhost:4566 for localstack
    S3_BUCKET: str = "nebula-ide-projects"

    # ── Execution Sandbox ─────────────────────────────────────────────────────
    SANDBOX_TIMEOUT_SECONDS: int = 10
    SANDBOX_MEMORY_LIMIT: str = "128m"
    SANDBOX_CPU_QUOTA: int = 50000        # 50% of one CPU
    SANDBOX_PIDS_LIMIT: int = 50
    SANDBOX_MAX_STDOUT_BYTES: int = 32768  # 32 KB
    SANDBOX_MAX_STDERR_BYTES: int = 8192   # 8 KB
    SANDBOX_MAX_CODE_SIZE_BYTES: int = 524288  # 512 KB

    # ── AI / Cost Controls ────────────────────────────────────────────────────
    # Using direct Anthropic API — ~30% cheaper than AWS Bedrock for same model
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-haiku-4-5-20251001"   # cheapest capable model
    AI_MAX_OUTPUT_TOKENS: int = 1024
    AI_MAX_CODE_LINES: int = 300          # truncate before sending to API
    AI_MAX_FINDINGS_PER_REVIEW: int = 15  # cap static analysis findings
    AI_DAILY_REVIEW_LIMIT: int = 20       # per-user per-day quota

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_EXECUTE: str = "10/minute"
    RATE_LIMIT_REVIEW: str = "5/minute"
    RATE_LIMIT_AUTH: str = "20/minute"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
