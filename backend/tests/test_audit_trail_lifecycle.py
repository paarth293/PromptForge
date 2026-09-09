import pytest

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.models.blueprint import AgentBlueprint
from backend.app.models.harden import HardeningLog
from backend.app.models.redteam import RedTeamReport
from backend.app.models.shield import PolicyObject
from backend.app.models.verify import VerificationScorecard
from backend.app.services.audit_service import AuditTrailService


@pytest.fixture
async def audit_env(tmp_path):
    db_file = tmp_path / "test_audit_trail.db"
    repo = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    service = AuditTrailService(repo=repo)
    return service, repo


@pytest.mark.asyncio
async def test_full_lifecycle_audit_trail_wiring_and_verification(audit_env):
    """
    Step 64 Done-When:
    The full lifecycle of one agent produces a complete, verifiable chain from birth to deployment.
    """
    service, repo = audit_env
    agent_id = "agent-lifecycle-001"
    tenant_id = "tenant-audit-test"

    # 1. Forge Complete Event
    bp = AgentBlueprint(
        blueprint_id=agent_id,
        spec_id="spec-audit-001",
        tenant_id=tenant_id,
        agent_name="AuditTestAgent",
        system_prompt="You are AuditTestAgent.",
        blueprint_hash="sha256-mock-bp-hash-001"
    )
    e1 = await service.record_forge_complete(bp)
    assert e1.prev_event_hash == "GENESIS"
    assert e1.event_type == "forge_complete"
    assert len(e1.event_hash) == 64

    # 2. Attack Verdict Event
    report = RedTeamReport(
        report_id="rpt-audit-001",
        blueprint_id=agent_id,
        tenant_id=tenant_id,
        total_attacks=12,
        blocked_count=10,
        degraded_count=1,
        compromised_count=1,
        survival_rate=0.833,
        report_hash="sha256-mock-report-hash-001"
    )
    e2 = await service.record_attack_verdict(report)
    assert e2.prev_event_hash == e1.event_hash
    assert e2.event_type == "attack_verdict"

    # 3. Patch Applied Event
    patch_log = HardeningLog(
        log_id="log-audit-001",
        initial_blueprint_id=agent_id,
        hardened_blueprint_id=f"{agent_id}-v2",
        initial_survival_rate=0.833,
        final_survival_rate=0.95,
        pass_count=2
    )
    e3 = await service.record_patch_applied(agent_id, tenant_id, patch_log)
    assert e3.prev_event_hash == e2.event_hash
    assert e3.event_type == "patch_applied"

    # 4. Verification Result Event
    scorecard = VerificationScorecard(
        scorecard_id="sc-audit-001",
        blueprint_id=agent_id,
        agent_name="AuditTestAgent",
        generated_set_score=(8, 8),
        goal_completion_score=(5, 5),
        consistency_score=(5, 5),
        adversarial_survival_score=(10, 12),
        promptforge_composite_score=94,
        formula_disclosed="PromptForge Standard Scorecard Formula v1",
        scorecard_hash="sha256-mock-scorecard-hash-001"
    )
    e4 = await service.record_verification_result(scorecard, tenant_id=tenant_id)
    assert e4.prev_event_hash == e3.event_hash
    assert e4.event_type == "verification_result"

    # 5. Policy Applied Event
    policy = PolicyObject(
        policy_id="pol-audit-001",
        spec_id="spec-audit-001",
        blueprint_id=agent_id,
        domain="finance",
        policy_hash="sha256-mock-policy-hash-001"
    )
    e5 = await service.record_policy_applied(policy, agent_id=agent_id, tenant_id=tenant_id)
    assert e5.prev_event_hash == e4.event_hash
    assert e5.event_type == "policy_applied"

    # 6. Deployment Event
    e6 = await service.record_deployment(
        agent_id=agent_id,
        tenant_id=tenant_id,
        endpoint_url="https://api.promptforge.ai/v1/agents/agent-lifecycle-001",
        version=1
    )
    assert e6.prev_event_hash == e5.event_hash
    assert e6.event_type == "deployment"

    # 7. Verification of the full 6-block continuous hash chain
    trail = await service.get_audit_trail(agent_id)
    assert len(trail) == 6

    is_valid, failed_idx, err = await service.verify_audit_trail(agent_id)
    assert is_valid is True
    assert failed_idx is None
    assert err is None


@pytest.mark.asyncio
async def test_audit_trail_detects_database_tampering(audit_env):
    """
    Validates that modifying any payload in the database invalidates the hash chain.
    """
    service, repo = audit_env
    agent_id = "agent-tamper-001"
    tenant_id = "tenant-tamper-test"

    bp = AgentBlueprint(
        blueprint_id=agent_id,
        spec_id="spec-01",
        tenant_id=tenant_id,
        agent_name="TamperTestAgent",
        system_prompt="Prompt",
        blueprint_hash="hash01"
    )
    e1 = await service.record_forge_complete(bp)
    await service.record_deployment(
        agent_id=agent_id,
        tenant_id=tenant_id,
        endpoint_url="https://api.promptforge.ai/v1/agents/agent-tamper-001"
    )

    # Initial chain is valid
    is_valid, _, _ = await service.verify_audit_trail(agent_id)
    assert is_valid is True

    # Tamper with block 1 payload directly in database
    async with repo._connect() as conn:
        import json
        cur = await conn.execute("SELECT data_json FROM audit_events WHERE event_id = ?;", (e1.event_id,))
        row = await cur.fetchone()
        event_dict = json.loads(row[0])
        event_dict["event_payload"]["agent_name"] = "MALICIOUSLY_ALTERED_NAME"
        await conn.execute(
            "UPDATE audit_events SET data_json = ? WHERE event_id = ?;",
            (json.dumps(event_dict), e1.event_id)
        )
        await conn.commit()

    # Verification must visibly detect the payload tamper at block 0
    is_valid_after, failed_idx, err = await service.verify_audit_trail(agent_id)
    assert is_valid_after is False
    assert failed_idx == 0
    assert "Tamper detected" in (err or "")
