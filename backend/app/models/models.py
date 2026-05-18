"""
Internal domain models (dataclasses).
These are used within the service layer and are separate from
the Pydantic API schemas to preserve separation of concerns.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class User:
    user_id: str
    email: str
    username: str
    role: str
    created_at: str
    last_login: str


@dataclass
class Project:
    project_id: str
    user_id: str
    name: str
    language: str
    description: str
    s3_prefix: str
    created_at: str
    updated_at: str


@dataclass
class ProjectFile:
    file_id: str
    project_id: str
    filename: str
    s3_key: str
    size_bytes: int
    updated_at: str


@dataclass
class ExecutionResult:
    exec_id: str
    user_id: str
    language: str
    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    timed_out: bool
    executed_at: str
    project_id: Optional[str] = None
    file_id: Optional[str] = None


@dataclass
class Finding:
    line: int
    severity: str        # error | warning | info
    category: str        # security | performance | style | correctness | other
    rule_id: str
    message: str
    explanation: str = ""
    fix: Optional[str] = None
    source: str = "static"  # static | ai


@dataclass
class ReviewResult:
    review_id: str
    user_id: str
    language: str
    overall_score: int
    summary: str
    findings: List[Finding]
    model_used: str
    tokens_used: int
    reviewed_at: str
    project_id: Optional[str] = None
    file_id: Optional[str] = None
