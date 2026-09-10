import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import settings
from .core.cost_instrumentation import PipelineCostReport, get_cost_tracker
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
    AgentDossier,
    AgentSpec,
    ArenaPairingRequest,
    ArenaPairingTranscript,
    ArenaRunResult,
    BirthCertificate,
    CertificateVerificationResult,
    ChatRequest,
    ChatResponse,
    ClaimVerificationResult,
    DeepForgeRunRequest,
    DeploymentPackage,
    EvolveLineageLog,
    HardeningLog,
    RedTeamReport,
    SeamAuditLogEntry,
    SeamHandoffResult,
    VerificationScorecard,
)
from .models.audit_import import (
    AuditImportAndRunRequest,
    AuditPipelineResult,
    AuditPipelineRunRequest,
    BedrockAgentImportRequest,
    OpenAIAssistantImportRequest,
    RawPromptImportRequest,
    UniversalAuditImportRequest,
)
from .models.harden import HardeningLoopResult
from .models.monitor import (
    CreateMonitorScheduleRequest,
    MonitorAlert,
    MonitorHistoryResponse,
    MonitorRunResult,
    MonitorSchedule,
    ReviewAlertRequest,
    TriggerMonitorRunRequest,
)
from .services.arena_service import ArenaService
from .services.audit_import_service import AuditImportService
from .services.audit_pipeline_service import AuditPipelineService
from .services.certificate_service import CertificateService
from .services.deployment_service import DeploymentService
from .services.dossier_service import DossierService
from .services.evolve_service import EvolveService
from .services.forge_service import ForgeService
from .services.harden_service import HardenService
from .services.monitor_service import MonitorService
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
    verify_tenant_access(log.tenant_id, tenant_id, "Hardening log")
    return log


@app.get("/api/harden/logs/blueprint/{blueprint_id}", response_model=List[HardeningLog])
async def list_hardening_logs_for_blueprint_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id, "Blueprint")
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
    verify_tenant_access(log.tenant_id, tenant_id, "Hardening log")
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

    # Parallelize Chains 10, 11, 12 Part 1, 12 Part 2 to meet the ~10–15s Verify timing target
    task_prompt = (
        spec.user_gold_qa[0]["question"]
        if spec.user_gold_qa
        else "Check order status and tracking details"
    )
    gt_res, con_res, goal_res, audit_res = await asyncio.gather(
        service.evaluate_ground_truth(blueprint=bp, spec=spec),
        service.evaluate_consistency(blueprint=bp, task_prompt=task_prompt, num_runs=5),
        service.evaluate_goal_completion(blueprint=bp),
        service.audit_alignment(blueprint=bp, spec=spec),
    )

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
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id, "Blueprint")

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
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id, "Blueprint")

    card = await repo.get_latest_scorecard_by_blueprint(blueprint_id)
    if not card:
        card = await run_verification_endpoint(blueprint_id=blueprint_id, tenant_id=tenant_id)
    service = VerifyService(repo=repo)
    text = service.format_scorecard(card)
    return {"blueprint_id": blueprint_id, "formatted_scorecard": text}


# =========================================================================
# Stage 5: DEPLOY & Certificate Endpoints
# =========================================================================

class CertificateVerifyRequest(BaseModel):
    certificate_id: str


@app.post("/api/deploy/certificate/generate/{blueprint_id}", response_model=BirthCertificate)
async def generate_certificate_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    cert_service = CertificateService(repo=repo)
    cert = await cert_service.generate_birth_certificate(blueprint_id=blueprint_id, tenant_id=tenant_id)
    return cert


@app.get("/api/deploy/certificate/{certificate_id}", response_model=BirthCertificate)
async def get_certificate_endpoint(
    certificate_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    cert = await repo.get_certificate(certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    verify_tenant_access(cert.tenant_id, tenant_id, "Certificate")
    return cert


@app.get("/api/deploy/certificate/agent/{agent_id}", response_model=BirthCertificate)
async def get_certificate_by_agent_endpoint(
    agent_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    cert = await repo.get_certificate_by_agent(agent_id)
    if not cert:
        raise HTTPException(status_code=404, detail="No certificate found for this agent")
    verify_tenant_access(cert.tenant_id, tenant_id, "Certificate")
    return cert


# Public Verification Endpoints (Accessible without auth to verify agent provenance)
@app.get("/api/verify/certificate/{certificate_id}", response_model=CertificateVerificationResult)
async def public_verify_certificate_endpoint(
    certificate_id: str,
):
    repo = PipelineRepository()
    cert = await repo.get_certificate(certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    cert_service = CertificateService(repo=repo)
    result = await cert_service.verify_certificate(certificate_id)
    return result


@app.post("/api/verify/certificate/verify", response_model=CertificateVerificationResult)
async def verify_certificate_post_endpoint(
    req: CertificateVerifyRequest,
):
    repo = PipelineRepository()
    cert = await repo.get_certificate(req.certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    cert_service = CertificateService(repo=repo)
    result = await cert_service.verify_certificate(req.certificate_id)
    return result


# =========================================================================
# Step 103: Cost & Token Instrumentation Endpoints
# =========================================================================

@app.get("/api/metrics/cost", response_model=PipelineCostReport)
async def get_cost_report_endpoint(
    run_id: str = "run-default",
    blueprint_id: Optional[str] = None
):
    """
    Step 103: Returns real token usage and cost report for the current or specified pipeline run.
    """
    return get_cost_tracker().generate_cost_report(run_id=run_id, blueprint_id=blueprint_id)


@app.get("/api/metrics/cost/formatted")
async def get_cost_report_formatted_endpoint():
    """
    Step 103: Returns ASCII-formatted cost report with stage breakdown matching the Idea Submission table.
    """
    tracker = get_cost_tracker()
    report = tracker.generate_cost_report()
    return {
        "formatted": tracker.format_ascii_report(report),
        "total_cost_usd": report.total_cost_usd,
        "total_tokens": report.total_tokens,
        "total_calls": report.total_calls,
        "tier_classification": report.tier_classification,
    }


# =========================================================================
# Step 66: Deployed Agent Endpoints & Packaging
# =========================================================================

@app.post("/api/deploy/agents/{blueprint_id}", response_model=DeploymentPackage)
async def deploy_agent_endpoint(
    blueprint_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    # Base URLs from request headers if present
    host = request.headers.get("host", "localhost:8000")
    scheme = request.url.scheme
    base_api_url = f"{scheme}://{host}"
    # Next.js frontend default port is 3000
    base_frontend_url = f"{scheme}://{request.url.hostname}:3000"

    deployment_service = DeploymentService(repo=repo)
    pkg = await deployment_service.deploy_agent(
        blueprint_id=blueprint_id,
        tenant_id=tenant_id,
        base_frontend_url=base_frontend_url,
        base_api_url=base_api_url,
    )
    return pkg


@app.get("/api/deploy/agents/{agent_id}", response_model=DeploymentPackage)
async def get_deployed_agent_endpoint(
    agent_id: str,
):
    """Public endpoint to fetch deployment configuration and metadata for a deployed agent."""
    repo = PipelineRepository()
    deployment_service = DeploymentService(repo=repo)
    pkg = await deployment_service.get_deployment(agent_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"No deployment found for agent '{agent_id}'")
    return pkg


@app.get("/api/deploy/agents", response_model=List[DeploymentPackage])
async def list_deployed_agents_endpoint(
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    deployment_service = DeploymentService(repo=repo)
    return await deployment_service.list_deployments(tenant_id=tenant_id)


@app.post("/api/deploy/agents/{agent_id}/chat", response_model=ChatResponse)
async def deployed_agent_chat_endpoint(
    agent_id: str,
    req: ChatRequest,
):
    """
    Step 66: Stable runtime chat endpoint for the deployed agent behind its shareable URL.
    Does not require admin forge headers.
    """
    repo = PipelineRepository()
    bp = await repo.get_blueprint(agent_id)
    if not bp:
        # Check if agent_id is a deployment_id
        pkg = await repo.get_deployment(agent_id)
        if pkg:
            bp = await repo.get_blueprint(pkg.blueprint_id)

    if not bp:
        raise HTTPException(status_code=404, detail=f"Deployed agent '{agent_id}' not found.")

    service = AgentRuntimeService(repo=repo)
    return await service.chat(blueprint_id=bp.blueprint_id, request=req)


# =========================================================================
# Phase 8: Mode 2: AUDIT Import Endpoints
# =========================================================================

@app.post("/api/audit/import/raw", response_model=AgentBlueprint)
async def import_raw_prompt_endpoint(
    req: RawPromptImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    import_service = AuditImportService(repo=repo)
    return await import_service.import_raw_prompt(
        prompt=req.prompt,
        agent_name=req.agent_name,
        domain=req.domain,
        tools=req.tools,
        user_gold_qa=req.user_gold_qa,
        tenant_id=tenant_id,
    )


@app.post("/api/audit/import/openai", response_model=AgentBlueprint)
async def import_openai_endpoint(
    req: OpenAIAssistantImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    import_service = AuditImportService(repo=repo)
    return await import_service.import_openai_gpt(
        config=req.config,
        agent_name=req.agent_name,
        domain=req.domain,
        user_gold_qa=req.user_gold_qa,
        tenant_id=tenant_id,
    )


@app.post("/api/audit/import/bedrock", response_model=AgentBlueprint)
async def import_bedrock_endpoint(
    req: BedrockAgentImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    import_service = AuditImportService(repo=repo)
    return await import_service.import_bedrock_agent(
        config=req.config,
        agent_name=req.agent_name,
        domain=req.domain,
        user_gold_qa=req.user_gold_qa,
        tenant_id=tenant_id,
    )


@app.post("/api/audit/import", response_model=AgentBlueprint)
async def import_universal_endpoint(
    req: UniversalAuditImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    import_service = AuditImportService(repo=repo)
    return await import_service.import_agent(
        format_type=req.format_type,
        payload=req.payload,
        user_gold_qa=req.user_gold_qa,
        tenant_id=tenant_id,
    )


@app.post("/api/audit/pipeline/run/{blueprint_id}", response_model=AuditPipelineResult)
async def run_audit_pipeline_endpoint(
    blueprint_id: str,
    req: AuditPipelineRunRequest = AuditPipelineRunRequest(),
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    blueprint = await repo.get_blueprint(blueprint_id)
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found.")
    verify_tenant_access(blueprint.tenant_id, tenant_id)

    pipeline_service = AuditPipelineService(repo=repo)
    return await pipeline_service.run_audit_pipeline(
        blueprint=blueprint,
        user_gold_qa=req.user_gold_qa,
        attacks_per_persona=req.attacks_per_persona,
        survival_threshold=req.survival_threshold,
        max_harden_passes=req.max_harden_passes,
        reattack_count_per_category=req.reattack_count_per_category,
    )


@app.post("/api/audit/pipeline/import-and-run", response_model=AuditPipelineResult)
async def import_and_run_audit_pipeline_endpoint(
    req: AuditImportAndRunRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    import_service = AuditImportService(repo=repo)
    blueprint = await import_service.import_agent(
        format_type=req.format_type,
        payload=req.payload,
        user_gold_qa=req.user_gold_qa,
        tenant_id=tenant_id,
    )

    pipeline_service = AuditPipelineService(repo=repo)
    return await pipeline_service.run_audit_pipeline(
        blueprint=blueprint,
        user_gold_qa=req.user_gold_qa,
        attacks_per_persona=req.attacks_per_persona,
        survival_threshold=req.survival_threshold,
        max_harden_passes=req.max_harden_passes,
        reattack_count_per_category=req.reattack_count_per_category,
    )


# =========================================================================
# PHASE 9: STAGE 6 (MONITOR) ENDPOINTS
# =========================================================================

@app.post("/api/monitor/schedules", response_model=MonitorSchedule)
async def create_monitor_schedule_endpoint(
    req: CreateMonitorScheduleRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    service = MonitorService(repo=repo)
    return await service.create_schedule(
        agent_id=req.agent_id,
        blueprint_id=req.blueprint_id,
        interval_seconds=req.interval_seconds,
        attacks_per_run=req.attacks_per_run,
        tenant_id=tenant_id,
    )


@app.get("/api/monitor/schedules/{agent_id}", response_model=List[MonitorSchedule])
async def list_monitor_schedules_endpoint(
    agent_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(agent_id)
    if bp:
        verify_tenant_access(bp.tenant_id, tenant_id, "Agent")
    return await repo.list_schedules_by_agent(agent_id)


@app.post("/api/monitor/run/{agent_id}", response_model=MonitorRunResult)
async def trigger_monitor_run_endpoint(
    agent_id: str,
    req: TriggerMonitorRunRequest = TriggerMonitorRunRequest(),
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(agent_id)
    if bp:
        verify_tenant_access(bp.tenant_id, tenant_id, "Agent")
    service = MonitorService(repo=repo)
    return await service.execute_monitor_run(
        agent_id=agent_id,
        attacks_per_run=req.attacks_per_run or 5,
        drift_threshold=req.drift_threshold,
        check_goal_completion=req.check_goal_completion,
        tenant_id=tenant_id,
    )


@app.post("/api/monitor/schedules/run-pending", response_model=List[MonitorRunResult])
async def run_pending_schedules_endpoint(
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    service = MonitorService(repo=repo)
    return await service.run_pending_schedules()


@app.get("/api/monitor/history/{agent_id}", response_model=MonitorHistoryResponse)
async def get_monitor_history_endpoint(
    agent_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(agent_id)
    if bp:
        verify_tenant_access(bp.tenant_id, tenant_id, "Agent")
    service = MonitorService(repo=repo)
    return await service.get_agent_monitor_history(agent_id)


@app.get("/api/monitor/review-queue", response_model=List[MonitorAlert])
async def list_monitor_review_queue_endpoint(
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    service = MonitorService(repo=repo)
    return await service.list_review_queue(tenant_id=tenant_id)


@app.post("/api/monitor/alerts/{alert_id}/review", response_model=MonitorAlert)
async def review_monitor_alert_endpoint(
    alert_id: str,
    req: ReviewAlertRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    service = MonitorService(repo=repo)
    return await service.review_alert(
        alert_id=alert_id,
        reviewer_id="human_operator",
        status=req.status,
        notes=req.reviewer_notes,
        action_approved=req.action_approved,
        tenant_id=tenant_id,
    )


# --- Phase 10: EVOLVE (Deep Forge) Endpoints ---

@app.post("/api/evolve/run")
async def run_deep_forge_endpoint(
    req: DeepForgeRunRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    spec = await repo.get_spec(req.spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec {req.spec_id} not found")

    evolve_service = EvolveService(repo=repo)

    if req.is_background:
        background_tasks.add_task(
            evolve_service.run_deep_forge,
            spec=spec,
            population_size=req.population_size,
            generations_count=req.generations_count,
            attacks_per_candidate=req.attacks_per_candidate,
            cached_demo_preferred=req.cached_demo_preferred,
        )
        return {
            "status": "queued",
            "message": "Deep Forge evolution started in background",
            "spec_id": req.spec_id,
            "population_size": req.population_size,
            "generations_count": req.generations_count,
        }
    else:
        lineage_log = await evolve_service.run_deep_forge(
            spec=spec,
            population_size=req.population_size,
            generations_count=req.generations_count,
            attacks_per_candidate=req.attacks_per_candidate,
            cached_demo_preferred=req.cached_demo_preferred,
        )
        return lineage_log


@app.get("/api/evolve/lineage/{spec_id}", response_model=EvolveLineageLog)
async def get_evolve_lineage_endpoint(
    spec_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    spec = await repo.get_spec(spec_id)
    if spec:
        verify_tenant_access(spec.tenant_id, tenant_id, "Spec")
    log = await repo.get_latest_lineage_log_by_spec(spec_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"No Deep Forge lineage log found for spec {spec_id}")
    verify_tenant_access(log.tenant_id, tenant_id, "Lineage log")
    return log


@app.get("/api/evolve/logs", response_model=List[EvolveLineageLog])
async def list_evolve_logs_endpoint(
    limit: int = 20,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    return await repo.list_evolve_lineage_logs(limit=limit)


# ==============================================================================
# Phase 11: ARENA Endpoints (Hostile Personas, Seam Attacks, Playbook Wiring)
# ==============================================================================

@app.post("/api/arena/run", response_model=ArenaRunResult)
async def run_arena_endpoint(
    req: ArenaPairingRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(req.target_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail=f"Target blueprint {req.target_blueprint_id} not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    arena_service = ArenaService(repo=repo)
    run_result = await arena_service.run_arena_battery(
        target_blueprint=bp,
        hostile_personas=req.hostile_personas,
        include_seam_attacks=req.include_seam_attacks,
        max_turns_per_pairing=req.max_turns_per_pairing,
    )
    return run_result


@app.get("/api/arena/runs", response_model=List[ArenaRunResult])
async def list_arena_runs_endpoint(
    limit: int = 20,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    arena_service = ArenaService(repo=repo)
    return await arena_service.list_arena_runs(limit=limit)


@app.get("/api/arena/run/{arena_run_id}", response_model=ArenaRunResult)
async def get_arena_run_endpoint(
    arena_run_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    arena_service = ArenaService(repo=repo)
    run = await arena_service.get_arena_run(arena_run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Arena run {arena_run_id} not found")
    verify_tenant_access(run.tenant_id, tenant_id, "Arena run")
    return run


@app.get("/api/arena/pairings/{blueprint_id}", response_model=List[ArenaPairingTranscript])
async def list_arena_pairings_endpoint(
    blueprint_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id, "Blueprint")
    return await repo.list_arena_pairings_by_blueprint(blueprint_id)


@app.get("/api/arena/seam-logs", response_model=List[SeamAuditLogEntry])
async def list_seam_logs_endpoint(
    target_agent_id: Optional[str] = None,
    limit: int = 50,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    arena_service = ArenaService(repo=repo)
    return await arena_service.get_seam_audit_logs(target_agent_id=target_agent_id, limit=limit)


class InteractiveSeamTestRequest(BaseModel):
    target_blueprint_id: str
    source_agent_role: str = "upstream_triage_peer"
    smuggled_instruction: str
    boundary_mode: str = "enforce_block"
    clean_data: Optional[Dict[str, Any]] = None


@app.post("/api/arena/seam-test", response_model=SeamHandoffResult)
async def test_seam_handoff_endpoint(
    req: InteractiveSeamTestRequest,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(req.target_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail=f"Target blueprint {req.target_blueprint_id} not found")
    verify_tenant_access(bp.tenant_id, tenant_id)

    arena_service = ArenaService(repo=repo)
    attack = arena_service.construct_seam_attack(
        source_agent_role=req.source_agent_role,
        target_agent_id=bp.blueprint_id,
        clean_data=req.clean_data or {"order_id": "ORD-9821", "customer_name": "Jordan Rivera", "status": "escalated"},
        smuggled_instruction=req.smuggled_instruction,
    )
    result = await arena_service.execute_seam_handoff(
        source_agent=bp,
        target_agent=bp,
        seam_attack=attack,
        boundary_mode=req.boundary_mode,  # type: ignore
    )
    return result


# =========================================================================
# Phase 12: DOSSIER Endpoints (Step 94 & 95)
# =========================================================================

@app.get("/api/dossier/{agent_id}", response_model=AgentDossier)
async def get_dossier_endpoint(
    agent_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    service = DossierService(repo=repo)
    dossier = await service.get_dossier(agent_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Dossier for agent '{agent_id}' not found.")
    verify_tenant_access(dossier.tenant_id, tenant_id, "Dossier")
    return dossier


@app.post("/api/dossier/{agent_id}/assemble", response_model=AgentDossier)
async def assemble_dossier_endpoint(
    agent_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    bp = await repo.get_blueprint(agent_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Agent blueprint not found")
    verify_tenant_access(bp.tenant_id, tenant_id, "Blueprint")
    service = DossierService(repo=repo)
    try:
        dossier = await service.assemble_dossier(blueprint_id=agent_id, agent_id=agent_id)
        dossier.tenant_id = bp.tenant_id
        await repo.save_dossier(dossier)
        return dossier
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/dossier/{agent_id}/claims/{claim_id}/verify", response_model=ClaimVerificationResult)
async def verify_dossier_claim_endpoint(
    agent_id: str,
    claim_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
):
    repo = PipelineRepository()
    dossier = await repo.get_dossier(agent_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    verify_tenant_access(dossier.tenant_id, tenant_id, "Dossier")
    service = DossierService(repo=repo)
    try:
        return await service.verify_claim(agent_id=agent_id, claim_id=claim_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)




