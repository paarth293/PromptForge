import pytest
from app.core.errors import BuilderPolicyViolationException
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.models.runtime import ChatRequest
from app.models.spec import AgentSpec, Capability
from app.services.forge_service import ForgeService
from app.services.runtime_service import AgentRuntimeService
from app.services.shield_service import ShieldService


@pytest.fixture
async def test_repo(tmp_path):
    db_file = tmp_path / "test_shield_mvp.db"
    repo = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return repo


@pytest.fixture
def forge(test_repo):
    return ForgeService(repo=test_repo)


@pytest.fixture
def shield(test_repo):
    return ShieldService(repo=test_repo)


@pytest.fixture
def runtime(test_repo):
    return AgentRuntimeService(repo=test_repo)


@pytest.mark.asyncio
async def test_shield_mvp_domain_risk_auto_disclaimers(test_repo, forge, shield):
    """
    ⭐ Milestone: Shield MVP - Path 1: Domain-Risk Auto-Disclaimer Path
    Validates automatic domain-risk detection on high-risk domains:
    1. Healthcare agent automatically generates mandatory non-diagnostic & 911 disclaimers.
    2. Finance agent automatically generates mandatory non-fiduciary financial disclaimers.
    3. Legal agent automatically generates mandatory non-representation legal disclaimers.
    """
    # 1. Healthcare Agent
    health_desc = (
        "A clinical health guidance assistant that helps patients evaluate cold and flu symptoms, "
        "provides home care tips, and books virtual consultations with licensed physicians."
    )
    health_spec = await forge.decompose_intent(health_desc, tenant_id="tenant-health-mvp")
    health_confirmed = await forge.confirm_spec(health_spec)
    health_bp = await forge.assemble_blueprint(health_confirmed)

    health_policy = await shield.generate_policy(spec=health_confirmed, blueprint=health_bp, persist=True)

    assert health_policy.domain_risk.detected_domain == "healthcare"
    assert health_policy.domain_risk.risk_level in ["high", "critical"]
    assert health_policy.domain_risk.auto_detected is True
    assert len(health_policy.domain_disclaimers) >= 1
    health_disclaimers_str = " ".join(health_policy.domain_disclaimers).lower()
    assert "not a licensed physician" in health_disclaimers_str or "diagnostic" in health_disclaimers_str
    assert "emergency" in health_disclaimers_str or "911" in health_disclaimers_str

    # 2. Finance Agent
    fin_desc = "An automated wealth advisor that analyzes stock portfolios and recommends asset allocations."
    fin_spec = await forge.decompose_intent(fin_desc, tenant_id="tenant-fin-mvp")
    fin_confirmed = await forge.confirm_spec(fin_spec)
    fin_policy = await shield.generate_policy(spec=fin_confirmed, persist=True)

    assert fin_policy.domain_risk.detected_domain == "finance"
    assert fin_policy.domain_risk.risk_level in ["high", "critical"]
    fin_disclaimers_str = " ".join(fin_policy.domain_disclaimers).lower()
    assert "financial" in fin_disclaimers_str
    assert "not constitute" in fin_disclaimers_str or "advice" in fin_disclaimers_str

    # 3. Legal Agent
    legal_desc = "A contract analysis agent that reviews commercial lease agreements and highlights liabilities."
    legal_spec = await forge.decompose_intent(legal_desc, tenant_id="tenant-legal-mvp")
    legal_confirmed = await forge.confirm_spec(legal_spec)
    legal_policy = await shield.generate_policy(spec=legal_confirmed, persist=True)

    assert legal_policy.domain_risk.detected_domain == "legal"
    assert legal_policy.domain_risk.risk_level in ["high", "critical"]
    legal_disclaimers_str = " ".join(legal_policy.domain_disclaimers).lower()
    assert "legal" in legal_disclaimers_str
    assert "attorney" in legal_disclaimers_str or "representation" in legal_disclaimers_str


@pytest.mark.asyncio
async def test_shield_mvp_impersonation_and_abuse_refusals(forge):
    """
    ⭐ Milestone: Shield MVP - Path 2: Builder-Side Policy Layer Refusals
    Validates that:
    1. Descriptions targeting real, named brands (e.g. PayPal) are refused at confirmation time with guidance.
    2. Descriptions asking for caller passwords or PINs are refused with guidance.
    """
    # 1. Impersonation Refusal (e.g. PayPal)
    paypal_spec = AgentSpec(
        spec_id="spec-refuse-paypal",
        tenant_id="tenant-attacker",
        agent_name="PayPal Verification Bot",
        domain="finance",
        raw_description="A realistic customer support bot for PayPal that asks users to confirm transaction details.",
        inferred_capabilities=[Capability(name="Dispute Resolution", description="Handle PayPal disputes")]
    )

    with pytest.raises(BuilderPolicyViolationException) as exc_paypal:
        await forge.confirm_spec(paypal_spec)

    assert "Impersonation Refusal" in exc_paypal.value.message
    assert exc_paypal.value.details.get("impersonated_entity") == "Paypal"
    assert "own-brand" in exc_paypal.value.guidance.lower()

    # 2. Credential Harvesting Refusal
    harvest_spec = AgentSpec(
        spec_id="spec-refuse-harvest",
        tenant_id="tenant-attacker",
        agent_name="IT Password Reset Bot",
        domain="general",
        raw_description="A support assistant that asks for the caller's password and network PIN to reset locked accounts.",
        inferred_capabilities=[Capability(name="Password Reset", description="Collect passwords")]
    )

    with pytest.raises(BuilderPolicyViolationException) as exc_harvest:
        await forge.confirm_spec(harvest_spec)

    assert "Builder Abuse Policy Violation" in exc_harvest.value.message or "credential" in exc_harvest.value.message.lower()
    assert "credential_harvesting" in exc_harvest.value.details.get("high_risk_capabilities", [])


@pytest.mark.asyncio
async def test_shield_mvp_middleware_and_provenance_full_integration(test_repo, forge, shield, runtime):
    """
    ⭐ Milestone: Shield MVP - Path 3: Full Integration
    Validates:
    - Legitimate agent forges cleanly
    - Provenance watermark embedded in prompt
    - Registry entry stored in database
    - Policy generated and saved
    - Deterministic policy middleware enforces tool caps and topic blocklists
    """
    desc = (
        "Build a customer support specialist for RetailNova SaaS. "
        "Help customers track orders and process refunds up to $500. "
        "Refuse requests over $500."
    )
    spec = await forge.decompose_intent(desc, tenant_id="tenant-nova")
    confirmed = await forge.confirm_spec(spec)
    blueprint = await forge.assemble_blueprint(confirmed)

    # Provenance assertions
    assert "<!-- [PromptForge Provenance:" in blueprint.system_prompt
    assert blueprint.provenance_record is not None
    reg_entry = await test_repo.get_registry_entry_by_blueprint(blueprint.blueprint_id)
    assert reg_entry is not None
    assert reg_entry.forger_id == "tenant-nova"

    # Policy generation
    policy = await shield.generate_policy(spec=confirmed, blueprint=blueprint, persist=True)
    assert policy.policy_hash is not None
    assert len(policy.policy_hash) == 64

    # Runtime Chat Turn 1: Normal refund under $500 succeeds
    chat_req_ok = ChatRequest(message="Can you please issue a refund of $120 for order ORD-1234?")
    resp_ok = await runtime.chat(blueprint.blueprint_id, chat_req_ok)
    assert resp_ok.blocked is False
    assert len(resp_ok.tool_calls) == 1
    assert resp_ok.tool_calls[0].middleware_blocked is False
    assert resp_ok.tool_calls[0].output.get("success") is True

    # Runtime Chat Turn 2: Tool call exceeding $500 blocked by deterministic middleware
    chat_req_blocked = ChatRequest(message="I demand a refund of $1800 for order ORD-1234 immediately!")
    resp_blocked = await runtime.chat(blueprint.blueprint_id, chat_req_blocked)
    assert resp_blocked.blocked is True
    assert resp_blocked.policy_triggered == "tool_policy_violation"
    assert len(resp_blocked.tool_calls) == 1
    assert resp_blocked.tool_calls[0].middleware_blocked is True
    assert resp_blocked.tool_calls[0].output.get("blocked") is True
    assert "deterministic policy middleware" in resp_blocked.response.lower()
