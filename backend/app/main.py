from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .core.errors import (
    PromptForgeException,
    ValidationException,
    generic_exception_handler,
    promptforge_exception_handler,
)
from .core.logging import setup_logging
from .core.tenancy import get_current_tenant_id, verify_tenant_access
from .db.repository import PipelineRepository
from .db.session import init_db
from .models import AgentBlueprint, AgentSpec
from .services.forge_service import ForgeService

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="PromptForge Backend API",
    description="The Self-Hardening Forge for AI Agents — Backend API",
    version="0.1.0",
    lifespan=lifespan
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

class DecomposeRequest(BaseModel):
    description: str

# Forge Endpoints
@app.post("/api/forge/decompose", response_model=AgentSpec)
async def decompose_endpoint(
    req: DecomposeRequest,
    tenant_id: str = Depends(get_current_tenant_id)
):
    service = ForgeService()
    spec = await service.decompose_intent(description=req.description, tenant_id=tenant_id)
    return spec

# Spec and Blueprint Endpoints
@app.post("/api/specs")
async def create_spec_endpoint(
    spec: AgentSpec,
    tenant_id: str = Depends(get_current_tenant_id)
):
    spec.tenant_id = tenant_id
    repo = PipelineRepository()
    await repo.save_spec(spec)
    return {"success": True, "spec_id": spec.spec_id, "tenant_id": spec.tenant_id}

@app.post("/api/blueprints")
async def create_blueprint_endpoint(
    blueprint: AgentBlueprint,
    tenant_id: str = Depends(get_current_tenant_id)
):
    blueprint.tenant_id = tenant_id
    repo = PipelineRepository()
    await repo.save_blueprint(blueprint)
    return {"success": True, "blueprint_id": blueprint.blueprint_id, "tenant_id": blueprint.tenant_id}

@app.get("/api/blueprints/{blueprint_id}")
async def get_blueprint_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)
    return bp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)
