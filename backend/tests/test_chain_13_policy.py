import pytest
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.models.spec import AgentSpec, Capability
from app.services.shield_service import ShieldService


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_shield.db"
    repository = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return repository


@pytest.fixture
def shield_service(repo):
    return ShieldService(repo=repo)


@pytest.mark.asyncio
async def test_chain_13_healthcare_auto_domain_risk_disclaimers(shield_service, repo):
    """
    Step 56 Done-When:
    A healthcare-agent spec automatically produces the required mandatory disclaimers
    without being asked.
    """
    spec = AgentSpec(
        spec_id="spec-health-001",
        tenant_id="tenant-health",
        agent_name="ClinicalTriageAssistant",
        raw_description="A clinical triage assistant that asks patients for symptoms, provides basic first-aid education, and books clinic appointments.",
        domain="healthcare",
        inferred_capabilities=[
            Capability(name="Symptom inquiry", description="Ask patient about symptoms"),
            Capability(name="First-aid education", description="Provide first-aid guidance"),
            Capability(name="Clinic booking", description="Schedule doctor visits")
        ],
        boundaries=["Never prescribe controlled medication", "Never diagnose terminal illness"]
    )

    policy = await shield_service.generate_policy(spec=spec, persist=True)

    # 1. Automatic Domain Risk Detection
    assert policy.domain_risk.detected_domain == "healthcare"
    assert policy.domain_risk.risk_level in ["high", "critical"]
    assert policy.domain_risk.auto_detected is True

    # 2. Mandatory Healthcare Disclaimers Auto-Inserted
    assert len(policy.domain_disclaimers) > 0
    joined_disclaimers = " ".join(policy.domain_disclaimers).lower()
    assert "not a licensed physician" in joined_disclaimers or "medical" in joined_disclaimers
    assert "emergency" in joined_disclaimers or "911" in joined_disclaimers

    # 3. Deterministic Policy Elements
    assert policy.rate_limits.requests_per_minute > 0
    assert policy.rate_limits.tokens_per_day > 0
    assert len(policy.topic_boundaries.whitelisted_topics) > 0
    assert len(policy.topic_boundaries.blocked_topics) > 0
    assert len(policy.escalation_rules) >= 2
    assert policy.audit_spec.pii_masking_enabled is True
    assert policy.fallback_behavior.on_rate_limit != ""
    assert policy.policy_hash is not None
    assert len(policy.policy_hash) == 64

    # 4. Database Persistence
    saved_policy = await repo.get_policy(policy.policy_id)
    assert saved_policy is not None
    assert saved_policy.policy_id == policy.policy_id
    assert saved_policy.domain_risk.detected_domain == "healthcare"


@pytest.mark.asyncio
async def test_chain_13_finance_auto_domain_risk_disclaimers(shield_service):
    """
    Finance agent spec automatically produces mandatory financial disclaimers.
    """
    spec = AgentSpec(
        spec_id="spec-fin-001",
        tenant_id="tenant-fin",
        agent_name="AlphaWealth Advisor",
        raw_description="An automated portfolio balancing agent that recommends stock allocations and crypto funds.",
        domain="finance",
        inferred_capabilities=[
            Capability(name="Portfolio balancing", description="Suggest asset allocations"),
            Capability(name="Asset education", description="Explain bond and equity concepts")
        ],
        boundaries=["Do not promise guaranteed returns", "Do not execute unconfirmed margin trades"]
    )

    policy = await shield_service.generate_policy(spec=spec, persist=False)

    assert policy.domain_risk.detected_domain == "finance"
    assert policy.domain_risk.risk_level in ["high", "critical"]
    joined_disclaimers = " ".join(policy.domain_disclaimers).lower()
    assert "financial" in joined_disclaimers
    assert "not constitute" in joined_disclaimers or "advice" in joined_disclaimers


@pytest.mark.asyncio
async def test_chain_13_legal_auto_domain_risk_disclaimers(shield_service):
    """
    Legal agent spec automatically produces mandatory legal disclaimers.
    """
    spec = AgentSpec(
        spec_id="spec-legal-001",
        tenant_id="tenant-legal",
        agent_name="LexClause Reviewer",
        raw_description="Review commercial lease contracts and highlight indemnification clauses.",
        domain="legal",
        inferred_capabilities=[
            Capability(name="Lease analysis", description="Extract indemnification terms"),
            Capability(name="Summary", description="List obligations")
        ],
        boundaries=["Cannot represent clients in court", "Cannot guarantee court rulings"]
    )

    policy = await shield_service.generate_policy(spec=spec, persist=False)

    assert policy.domain_risk.detected_domain == "legal"
    assert policy.domain_risk.risk_level in ["high", "critical"]
    joined_disclaimers = " ".join(policy.domain_disclaimers).lower()
    assert "legal" in joined_disclaimers
    assert "attorney" in joined_disclaimers or "representation" in joined_disclaimers


@pytest.mark.asyncio
async def test_chain_13_general_customer_support_policy(shield_service):
    """
    Customer support agent policy generation with baseline low/medium risk.
    """
    spec = AgentSpec(
        spec_id="spec-support-001",
        tenant_id="tenant-support",
        agent_name="SaaS Support Bot",
        raw_description="Assist users with password resets, invoice lookups, and account settings.",
        domain="customer_support",
        inferred_capabilities=[
            Capability(name="Ticket lookup", description="Check status"),
            Capability(name="Password reset", description="Send reset link")
        ],
        boundaries=["Never view plaintext credentials"]
    )

    policy = await shield_service.generate_policy(spec=spec, persist=False)

    assert policy.domain_risk.detected_domain == "customer_support"
    assert len(policy.escalation_rules) >= 1
    assert policy.builder_policy_compliance is True
