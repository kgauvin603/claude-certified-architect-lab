from enum import Enum
from typing import Any

from pydantic import BaseModel


class ErrorCategory(str, Enum):
    VALIDATION_ERROR = "validation_error"
    TRANSIENT_ERROR = "transient_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND = "not_found"
    POLICY_GAP = "policy_gap"
    FATAL_ERROR = "fatal_error"


class ToolError(BaseModel):
    category: ErrorCategory
    message: str
    retryable: bool = False
    suggested_action: str | None = None


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] | None = None
    error: ToolError | None = None
