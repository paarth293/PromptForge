from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.errors import (
    PromptForgeException,
    ValidationException,
    generic_exception_handler,
    promptforge_exception_handler,
)
from .core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="PromptForge Backend API",
    description="The Self-Hardening Forge for AI Agents — Backend API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(PromptForgeException, promptforge_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    import uuid
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "promptforge-backend",
        "version": "0.1.0",
        "environment": settings.promptforge_env
    }

@app.get("/api/test/error")
async def test_error_endpoint():
    """Forces an error to test the standardized error shape."""
    raise ValidationException("Forced test validation error", details={"field": "test_input"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)
