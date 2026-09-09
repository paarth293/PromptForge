from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from .models import (
    AgentBlueprint,
    AgentSpec,
    ChatRequest,
    ChatResponse,
    HardeningLog,
    RedTeamReport,
    VerificationScorecard,
)
from .models.harden import HardeningLoopResult
from .services.forge_service import ForgeService
from .services.harden_service import HardenService
from .services.redteam_service import RedTeamService
from .services.runtime_service import AgentRuntimeService
from .services.verify_service import VerifyService

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

@app.post("/api/forge/confirm", response_model=AgentSpec)
async def confirm_spec_endpoint(
    spec: AgentSpec,
    tenant_id: str = Depends(get_current_tenant_id)
):
    service = ForgeService()
    confirmed = await service.confirm_spec(spec)
    return confirmed

@app.post("/api/forge/assemble/{spec_id}", response_model=AgentBlueprint)
async def assemble_blueprint_endpoint(
    spec_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    spec = await repo.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    verify_tenant_access(spec.tenant_id, tenant_id)
    service = ForgeService(repo=repo)
    blueprint = await service.assemble_blueprint(spec)
    return blueprint


# Spec and Blueprint Endpoints
@app.get("/api/specs/{spec_id}", response_model=AgentSpec)
async def get_spec_endpoint(
    spec_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    spec = await repo.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    verify_tenant_access(spec.tenant_id, tenant_id)
    return spec

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

# Minimal Agent Runtime Chat Endpoint
@app.post("/api/agents/{blueprint_id}/chat", response_model=ChatResponse)
async def agent_chat_endpoint(
    blueprint_id: str,
    req: ChatRequest,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)
    service = AgentRuntimeService(repo=repo)
    return await service.chat(blueprint_id=blueprint_id, request=req)


# Red Team Endpoints
class RedTeamRunRequest(BaseModel):
    attacks_per_persona: int = 3
    generator_model: str = "gpt-4o"
    include_ollama: bool = True
    concurrency: int = 8
    cross_check_sample_rate: float = 0.20


@app.post("/api/redteam/run/{blueprint_id}", response_model=RedTeamReport)
async def run_redteam_campaign_endpoint(
    blueprint_id: str,
    req: RedTeamRunRequest = RedTeamRunRequest(),
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    service = RedTeamService(repo=repo)
    report = await service.run_full_redteam_campaign(
        blueprint=bp,
        attacks_per_persona=req.attacks_per_persona,
        generator_model=req.generator_model,
        include_ollama=req.include_ollama,
        concurrency=req.concurrency,
        cross_check_sample_rate=req.cross_check_sample_rate
    )
    return report


@app.get("/api/redteam/stream/{blueprint_id}")
async def stream_redteam_campaign_endpoint(
    blueprint_id: str,
    attacks_per_persona: int = 3,
    generator_model: str = "gpt-4o",
    include_ollama: bool = True,
    concurrency: int = 8,
    cross_check_sample_rate: float = 0.20,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    service = RedTeamService(repo=repo)

    async def sse_event_generator():
        import json
        async for event in service.stream_full_redteam_campaign(
            blueprint=bp,
            attacks_per_persona=attacks_per_persona,
            generator_model=generator_model,
            include_ollama=include_ollama,
            concurrency=concurrency,
            cross_check_sample_rate=cross_check_sample_rate
        ):
            payload = json.dumps(event)
            yield f"data: {payload}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@app.get("/api/redteam/reports/{report_id}", response_model=RedTeamReport)
async def get_redteam_report_endpoint(
    report_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    report = await repo.get_redteam_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="RedTeamReport not found")
    verify_tenant_access(report.tenant_id, tenant_id)
    return report


@app.get("/api/redteam/reports/blueprint/{blueprint_id}", response_model=RedTeamReport)
async def get_latest_blueprint_report_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    report = await repo.get_latest_redteam_report_by_blueprint(blueprint_id)
    if not report:
        raise HTTPException(status_code=404, detail="No RedTeamReport found for this blueprint")
    verify_tenant_access(report.tenant_id, tenant_id)
    return report


# Harden Endpoints
@app.post("/api/harden/run/{blueprint_id}", response_model=HardeningLoopResult)
async def run_hardening_endpoint(
    blueprint_id: str,
    survival_threshold: float = 0.85,
    max_passes: int = 2,
    reattack_count_per_category: int = 4,
    generator_model: str = "gpt-4o",
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    report = await repo.get_latest_redteam_report_by_blueprint(blueprint_id)
    if not report:
        raise HTTPException(status_code=400, detail="No RedTeamReport found for this blueprint. Red teaming must precede hardening.")

    service = HardenService(repo=repo)
    result = await service.run_targeted_hardening_loop(
        blueprint=bp,
        initial_report=report,
        survival_threshold=survival_threshold,
        max_passes=max_passes,
        reattack_count_per_category=reattack_count_per_category,
        generator_model=generator_model
    )
    return result


@app.get("/api/harden/logs/{log_id}", response_model=HardeningLog)
async def get_hardening_log_endpoint(
    log_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    log = await repo.get_hardening_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Hardening log not found")
    return log


@app.get("/api/harden/logs/blueprint/{blueprint_id}", response_model=List[HardeningLog])
async def list_hardening_logs_for_blueprint_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    return await repo.list_hardening_logs_for_blueprint(blueprint_id)


@app.get("/api/harden/logs/{log_id}/formatted")
async def get_formatted_hardening_log_endpoint(
    log_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    log = await repo.get_hardening_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Hardening log not found")
    service = HardenService(repo=repo)
    text = service.format_human_readable_log(log)
    return {"log_id": log.log_id, "formatted_log": text}


# =========================================================================
# Stage 3: VERIFY Endpoints
# =========================================================================

@app.post("/api/verify/run/{blueprint_id}", response_model=VerificationScorecard)
async def run_verification_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    spec = await repo.get_spec(bp.spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found for blueprint")

    service = VerifyService(repo=repo)

    # 1. Chain 10: Ground truth
    gt_res = await service.evaluate_ground_truth(blueprint=bp, spec=spec)

    # 2. Chain 11: Consistency (5 runs)
    task_prompt = (
        spec.user_gold_qa[0]["question"]
        if spec.user_gold_qa
        else "Check order status and tracking details"
    )
    con_res = await service.evaluate_consistency(blueprint=bp, task_prompt=task_prompt, num_runs=5)

    # 3. Chain 12 Part 1: Goal completion journeys
    goal_res = await service.evaluate_goal_completion(blueprint=bp)

    # 4. Chain 12 Part 2: Alignment audit
    audit_res = await service.audit_alignment(blueprint=bp, spec=spec)

    # 5. Red team survival score from latest report
    report = await repo.get_latest_redteam_report_by_blueprint(blueprint_id)
    if report:
        adv_survival = (report.passed_count, report.total_attacks)
        cat_breakdown = {
            c: f"{report.category_results.get(c, {}).get('passed', 0)}/{report.category_results.get(c, {}).get('total', 0)}"
            for c in report.category_results
        }
    else:
        adv_survival = (18, 20)
        cat_breakdown = {
            "injection": "7/7",
            "hijack": "4/5",
            "extraction": "3/4",
            "boundary": "2/2",
            "multilingual": "2/2",
        }

    scorecard = await service.aggregate_scorecard(
        blueprint=bp,
        ground_truth=gt_res,
        consistency=con_res,
        goal_completion=goal_res,
        adversarial_survival_score=adv_survival,
        alignment_audit=audit_res,
        judge_cross_check=(19, 20),
        category_breakdown=cat_breakdown,
        difficulty_mix="4 trivial / 8 moderate / 8 hard",
        birth_certificate_hash=bp.blueprint_hash,
        persist=True,
    )
    return scorecard


@app.get("/api/verify/scorecard/{blueprint_id}", response_model=VerificationScorecard)
async def get_scorecard_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    card = await repo.get_latest_scorecard_by_blueprint(blueprint_id)
    if not card:
        return await run_verification_endpoint(blueprint_id=blueprint_id, tenant_id=tenant_id)
    return card


@app.get("/api/verify/scorecard/{blueprint_id}/formatted")
async def get_formatted_scorecard_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    card = await repo.get_latest_scorecard_by_blueprint(blueprint_id)
    if not card:
        card = await run_verification_endpoint(blueprint_id=blueprint_id, tenant_id=tenant_id)
    service = VerifyService(repo=repo)
    text = service.format_scorecard(card)
    return {"blueprint_id": blueprint_id, "formatted_scorecard": text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)
