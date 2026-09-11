import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("promptforge.error")

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class APIErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str

class PromptForgeException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

class ValidationException(PromptForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=422, details=details)

class PolicyViolationException(PromptForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="POLICY_VIOLATION", status_code=403, details=details)

class BuilderPolicyViolationException(PolicyViolationException):
    def __init__(self, message: str, guidance: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        merged = details.copy() if details else {}
        if guidance:
            merged["guidance"] = guidance
        super().__init__(message, details=merged)
        self.code = "BUILDER_POLICY_VIOLATION"
        self.guidance = guidance

class LLMException(PromptForgeException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="LLM_EXECUTION_ERROR", status_code=502, details=details)

async def promptforge_exception_handler(request: Request, exc: PromptForgeException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"[{exc.code}] {exc.message} (req_id: {req_id})", extra={"request_id": req_id})
    return JSONResponse(
        status_code=exc.status_code,
        content=APIErrorResponse(
            success=False,
            error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details),
            request_id=req_id
        ).model_dump()
    )

async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"Unhandled error: {str(exc)} (req_id: {req_id})", exc_info=True, extra={"request_id": req_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIErrorResponse(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. Please contact support quoting the request_id."
            ),
            request_id=req_id
        ).model_dump()
    )
