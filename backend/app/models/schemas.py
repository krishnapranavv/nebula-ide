"""
Pydantic API schemas — request validation and response serialisation.
Strict validators prevent oversized payloads that inflate AI token costs.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal
import re

Language = Literal["python", "javascript", "cpp"]
Severity = Literal["error", "warning", "info"]
Category = Literal["security", "performance", "style", "correctness", "other"]


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username may only contain letters, numbers, _ and -")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    username: str
    role: str
    created_at: str


# ── Projects ──────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    language: Language
    description: str = Field(default="", max_length=500)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ProjectResponse(BaseModel):
    project_id: str
    user_id: str
    name: str
    language: Language
    description: str
    s3_prefix: str
    created_at: str
    updated_at: str


# ── Files ─────────────────────────────────────────────────────────────────────

class CreateFileRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=524288)

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, v: str) -> str:
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Filename cannot contain path separators")
        if not re.match(r"^[a-zA-Z0-9_\-.]+$", v):
            raise ValueError("Filename contains invalid characters")
        return v


class UpdateFileRequest(BaseModel):
    content: str = Field(max_length=524288)


class FileResponse(BaseModel):
    file_id: str
    project_id: str
    filename: str
    s3_key: str
    size_bytes: int
    updated_at: str


class FileContentResponse(BaseModel):
    file_id: str
    filename: str
    content: str
    updated_at: str


# ── Execution ─────────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=524288)
    language: Language
    stdin: str = Field(default="", max_length=4096)
    file_id: Optional[str] = None
    project_id: Optional[str] = None


class ExecutionResponse(BaseModel):
    exec_id: str
    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    timed_out: bool
    language: Language
    executed_at: str


# ── AI Review ─────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    code: str = Field(min_length=1, max_length=524288)
    language: Language
    file_id: Optional[str] = None
    project_id: Optional[str] = None


class FindingSchema(BaseModel):
    line: int
    severity: Severity
    category: Category
    rule_id: str
    message: str
    explanation: str
    fix: Optional[str] = None
    source: str = "static"


class ReviewResponse(BaseModel):
    review_id: str
    overall_score: int = Field(ge=1, le=10)
    summary: str
    findings: List[FindingSchema]
    model_used: str
    tokens_used: int
    reviewed_at: str
    language: Language


# ── Shared ────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    ai_provider: str
