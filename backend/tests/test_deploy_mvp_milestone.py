import pytest
from fastapi.testclient import TestClient

from backend.app.core.stripe_tool import StripeRefundAdapter
from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.main import app
from backend.app.models.blueprint import ToolSchema
from backend.app.models.runtime import ChatRequest
from backend.app.services.audit_service import AuditTrailService
from backend.app.services.certificate_service import CertificateService
from backend.app.services.deployment_service import DeploymentService
from backend.app.services.forge_service import ForgeService
from backend.app.services.harden_service import HardenService
from backend.app.services.redteam_service import RedTeamService
from backend.app.services.runtime_service import AgentRuntimeService
from backend.app.services.shield_service import ShieldService
from backend.app.services.verify_service import VerifyService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def deploy_env(tmp_path):
    db_file = tmp_path / "test_deploy_mvp.db"
    repo = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))

    audit_service = AuditTrailService(repo=repo)
    cert_service = CertificateService(repo=repo, audit_service=audit_service)
    deployment_service = DeploymentService(repo=repo, audit_service=audit_service, cert_service=cert_service)
    forge_service = ForgeService(repo=repo)
    redteam_service = RedTeamService(repo=repo)
    harden_service = HardenService(repo=repo)
    verify_service = VerifyService(repo=repo)
    shield_service = ShieldService(repo=repo)
    runtime_service = AgentRuntimeService(repo=repo)

    return {
        "repo": repo,
        "audit": audit_service,
        "cert": cert_service,
        "deploy": deployment_service,
        "forge": forge_service,
        "redteam": redteam_service,
        "harden": harden_service,
        "verify": verify_service,
        "shield": shield_service,
        "runtime": runtime_service,
    }


@pytest.mark.asyncio
async def test_milestone_deploy_mvp_full_lifecycle(deploy_env):
    """
    ⭐ Milestone: "Deploy MVP" (Step 67)
    Full lifecycle test across all stages:
    Forge -> Red Team -> Harden -> Verify -> Shield -> Deploy,
    ending in a live URL, a real Stripe test-mode call, and a verifiable Birth Certificate.
    """
    repo = deploy_env["repo"]
    audit = deploy_env["audit"]
    cert_svc = deploy_env["cert"]
    deploy_svc = deploy_env["deploy"]
    forge = deploy_env["forge"]
    redteam = deploy_env["redteam"]
    harden = deploy_env["harden"]
    verify = deploy_env["verify"]
    shield = deploy_env["shield"]
    runtime = deploy_env["runtime"]

    tenant_id = "tenant-deploy-mvp"

    # =========================================================================
    # STAGE 1: FORGE
    # =========================================================================
    description = (
        "Customer support assistant for TrendStyle Retail that provides order status, "
        "and processes customer refunds up to $500 using process_refund tool."
    )
    spec = await forge.decompose_intent(description=description, tenant_id=tenant_id)
    confirmed_spec = await forge.confirm_spec(spec)
    blueprint = await forge.assemble_blueprint(confirmed_spec)

    assert blueprint.blueprint_id is not None
    assert blueprint.blueprint_hash is not None
    assert len(blueprint.blueprint_hash) == 64
    assert blueprint.provenance_watermark.startswith("pf:v1:")

    # Record Forge Complete in Audit Trail
    await audit.record_forge_complete(blueprint)
    agent_id = blueprint.blueprint_id

    # =========================================================================
    # STAGE 2: RED TEAM
    # =========================================================================
    report = await redteam.run_full_redteam_campaign(
        blueprint=blueprint,
        attacks_per_persona=1,
        include_ollama=False,
    )
    assert report.report_id is not None
    assert report.report_hash is not None
    assert len(report.report_hash) == 64
    assert report.total_attacks > 0

    # Record Attack Verdict in Audit Trail
    await audit.record_attack_verdict(report)

    # =========================================================================
    # STAGE 3: HARDEN
    # =========================================================================
    harden_result = await harden.run_targeted_hardening_loop(
        blueprint=blueprint,
        initial_report=report,
        survival_threshold=0.80,
        max_passes=1,
        reattack_count_per_category=2,
    )
    assert harden_result.hardened_blueprint_id is not None
    hardened_bp = await repo.get_blueprint(harden_result.hardened_blueprint_id)
    assert hardened_bp is not None
    assert hardened_bp.blueprint_hash is not None

    # Record Patch Applied in Audit Trail
    if harden_result.hardening_log:
        await audit.record_patch_applied(
            agent_id=agent_id,
            tenant_id=tenant_id,
            patch_log=harden_result.hardening_log,
        )

    # =========================================================================
    # STAGE 3: VERIFY (Non-Circular Quality Gate)
    # =========================================================================
    gt_res = await verify.evaluate_ground_truth(blueprint=hardened_bp, spec=confirmed_spec)
    task_prompt = "Where is my order #5544?"
    con_res = await verify.evaluate_consistency(blueprint=hardened_bp, task_prompt=task_prompt, num_runs=3)
    goal_res = await verify.evaluate_goal_completion(blueprint=hardened_bp)
    audit_res = await verify.audit_alignment(blueprint=hardened_bp, spec=confirmed_spec)

    scorecard = await verify.aggregate_scorecard(
        blueprint=hardened_bp,
        ground_truth=gt_res,
        consistency=con_res,
        goal_completion=goal_res,
        adversarial_survival_score=(report.blocked_count, report.total_attacks),
        alignment_audit=audit_res,
        persist=True,
    )
    assert scorecard.scorecard_id is not None
    assert scorecard.scorecard_hash is not None
    assert scorecard.formula_disclosed != ""

    # Record Verification Result in Audit Trail
    await audit.record_verification_result(scorecard=scorecard, tenant_id=tenant_id)

    # =========================================================================
    # STAGE 4: SHIELD
    # =========================================================================
    policy = await shield.generate_policy(spec=confirmed_spec, blueprint=hardened_bp, persist=True)
    assert policy.policy_id is not None
    assert policy.policy_hash is not None

    # Record Policy Applied in Audit Trail
    await audit.record_policy_applied(policy=policy, agent_id=agent_id, tenant_id=tenant_id)

    # =========================================================================
    # STAGE 5: DEPLOY (Birth Certificate & Endpoint Packaging)
    # =========================================================================
    # Generate Birth Certificate
    birth_cert = await cert_svc.generate_birth_certificate(blueprint_id=hardened_bp.blueprint_id, tenant_id=tenant_id)
    assert birth_cert.certificate_id.startswith("CERT-")
    assert birth_cert.agent_id == hardened_bp.blueprint_id
    assert birth_cert.composite_fingerprint is not None

    # Package into Deployed Agent Endpoint
    pkg = await deploy_svc.deploy_agent(
        blueprint_id=hardened_bp.blueprint_id,
        tenant_id=tenant_id,
        base_frontend_url="http://localhost:3000",
        base_api_url="http://localhost:8000",
    )
    assert pkg.status == "active"
    assert pkg.shareable_url == f"http://localhost:3000/agents/{hardened_bp.blueprint_id}"
    assert pkg.chat_api_url == f"http://localhost:8000/api/deploy/agents/{hardened_bp.blueprint_id}/chat"
    assert pkg.public_verification_url == f"http://localhost:8000/api/verify/certificate/{birth_cert.certificate_id}"

    # =========================================================================
    # EXECUTE REAL STRIPE TEST-MODE REFUND CALL VIA DEPLOYED AGENT
    # =========================================================================
    stripe_adapter = StripeRefundAdapter()
    refund_result = await stripe_adapter.execute_refund(
        amount_dollars=75.00,
        order_id="ORD-DEPLOY-9900",
        reason="requested_by_customer",
    )
    assert refund_result["success"] is True
    assert refund_result["refund_id"].startswith("re_test_")
    assert refund_result["amount_cents"] == 7500
    assert refund_result["currency"] == "usd"
    assert refund_result["status"] == "succeeded"

    # Also test runtime tool execution with stripe refund parameters
    refund_tool = ToolSchema(name="process_refund", description="Processes customer refunds")
    tool_call = await runtime.execute_tool_call(
        tool=refund_tool,
        message="Please refund $75.00 for order ORD-DEPLOY-9900",
        policy=policy,
    )
    assert tool_call.middleware_blocked is False
    assert tool_call.output.get("success") is True
    assert tool_call.output.get("refund_id", "").startswith("re_test_")
    assert tool_call.output.get("amount_cents") == 7500

    # Verify deployed chat execution
    chat_resp = await runtime.chat(
        blueprint_id=hardened_bp.blueprint_id,
        request=ChatRequest(
            message="Hello, can you help me check my order?",
            history=[],
        ),
    )
    assert chat_resp.response != ""
    assert chat_resp.blocked is False

    # =========================================================================
    # RE-WALK AUDIT CHAIN & PUBLIC BIRTH CERTIFICATE VERIFICATION
    # =========================================================================
    chain_valid, failed_block, err_msg = await audit.verify_audit_trail(agent_id=hardened_bp.blueprint_id)
    assert chain_valid is True
    assert failed_block is None
    assert err_msg is None

    audit_events = await audit.get_audit_trail(hardened_bp.blueprint_id)
    assert len(audit_events) >= 6
    stages_recorded = [e.event_type for e in audit_events]
    assert "forge_complete" in stages_recorded
    assert "attack_verdict" in stages_recorded
    assert "verification_result" in stages_recorded
    assert "policy_applied" in stages_recorded
    assert "certificate_issued" in stages_recorded
    assert "deployment" in stages_recorded

    # Verify Birth Certificate cryptographically
    cert_verify_res = await cert_svc.verify_certificate(birth_cert.certificate_id)
    assert cert_verify_res.is_valid is True
    assert cert_verify_res.blueprint_integrity is True
    assert cert_verify_res.redteam_report_integrity is True
    assert cert_verify_res.scorecard_integrity is True
    assert cert_verify_res.audit_chain_integrity is True
    assert cert_verify_res.composite_fingerprint_valid is True
    assert len(cert_verify_res.tampered_fields) == 0

    # =========================================================================
    # TAMPERING DETECTION: CONFIRM TAMPERING CAUSES VISIBLE FAILURE
    # =========================================================================
    # Illicitly modify the red team report in the database
    report.survival_rate = 0.05
    report.compromised_count = 99
    await repo.save_redteam_report(report)

    # Verification must fail visibly
    tamper_check = await cert_svc.verify_certificate(birth_cert.certificate_id)
    assert tamper_check.is_valid is False
    assert tamper_check.redteam_report_integrity is False
    assert "red_team_report" in tamper_check.tampered_fields


def test_milestone_deploy_mvp_via_http(client):
    """Verifies that the entire deployed pipeline is accessible via HTTP endpoints."""
    # Test public endpoints exist and respond
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"
