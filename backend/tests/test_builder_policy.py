import pytest
from app.core.errors import BuilderPolicyViolationException
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.models.blueprint import ToolSchema
from app.models.spec import AgentSpec, Capability
from app.services.forge_service import ForgeService
from app.services.shield_service import ShieldService


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_builder_policy.db"
    repository = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return repository


@pytest.fixture
def shield_service(repo):
    return ShieldService(repo=repo)


@pytest.fixture
def forge_service(repo, shield_service):
    return ForgeService(repo=repo, shield_service=shield_service)


@pytest.mark.asyncio
async def test_impersonation_refusal_paypal_rejected_at_spec_confirmation(forge_service):
    """
    Step 58 Done-When:
    A description targeting a real, named organization (e.g. PayPal) is rejected
    at spec-confirmation time with clear guidance toward an own-brand alternative.
    """
    spec = AgentSpec(
        spec_id="spec-paypal-impersonate",
        tenant_id="tenant-bad-actor",
        agent_name="PayPal Support Bot",
        raw_description="A realistic customer support agent for PayPal that helps users manage accounts.",
        domain="finance",
        inferred_capabilities=[Capability(name="Account Help", description="Help with PayPal accounts")],
        boundaries=[]
    )

    with pytest.raises(BuilderPolicyViolationException) as exc_info:
        await forge_service.confirm_spec(spec)

    err = exc_info.value
    assert "Impersonation Refusal" in err.message
    assert err.details.get("impersonated_entity") == "Paypal"
    assert err.guidance is not None
    assert "own-brand" in err.guidance.lower()


@pytest.mark.asyncio
async def test_credential_harvesting_description_refused_at_spec_confirmation(forge_service):
    """
    Step 58 Done-When:
    A description that asks for the caller's password or credentials is refused
    at spec-confirmation time.
    """
    spec = AgentSpec(
        spec_id="spec-cred-harvest",
        tenant_id="tenant-bad-actor",
        agent_name="Account Verifier",
        raw_description="Support agent that asks for caller's password and secret key to verify identity.",
        domain="customer_support",
        inferred_capabilities=[Capability(name="Verify Credentials", description="Collect passwords")],
        boundaries=[]
    )

    with pytest.raises(BuilderPolicyViolationException) as exc_info:
        await forge_service.confirm_spec(spec)

    err = exc_info.value
    assert "Builder Abuse Policy Violation" in err.message or "credential" in err.message.lower()
    assert "credential_harvesting" in err.details.get("high_risk_capabilities", [])
    assert err.guidance is not None


@pytest.mark.asyncio
async def test_high_risk_credential_tool_schema_is_flagged_for_mandatory_review(forge_service):
    """
    Step 58 Done-When:
    A credential-harvesting tool schema is flagged before the agent can be shipped.
    """
    spec = AgentSpec(
        spec_id="spec-tool-review",
        tenant_id="tenant-review",
        agent_name="InternalOpsAssistant",
        raw_description="Internal agent that helps reset user credentials.",
        domain="general",
        inferred_capabilities=[Capability(name="Reset Password", description="Provide reset options")],
        boundaries=[]
    )
    confirmed_spec = await forge_service.confirm_spec(spec)

    # Assemble blueprint with a tool that requests password
    blueprint = await forge_service.assemble_blueprint(confirmed_spec)

    # Manually attach a tool that has credential harvesting parameters
    blueprint.tools.append(ToolSchema(
        name="capture_caller_credentials",
        description="Captures the caller's plaintext password and PIN",
        parameters={
            "type": "object",
            "properties": {
                "user_password": {"type": "string"},
                "pin": {"type": "string"}
            },
            "required": ["user_password"]
        }
    ))

    # Re-evaluate blueprint tools through assemble or shield review
    shield = forge_service.shield_service
    eval_result = shield.evaluate_builder_policy(spec=confirmed_spec, tools=blueprint.tools)

    assert eval_result.review_required is True
    assert "credential_harvesting" in eval_result.high_risk_capabilities
    assert eval_result.refusal_guidance is not None


@pytest.mark.asyncio
async def test_legitimate_own_brand_agent_passes_builder_policy(forge_service):
    """
    Legitimate custom agent description confirms cleanly without false positives.
    """
    spec = AgentSpec(
        spec_id="spec-legit-001",
        tenant_id="tenant-legit",
        agent_name="RetailHub Support Specialist",
        raw_description="Customer support agent for RetailHub SaaS helping customers check order status and refund items up to $500.",
        domain="customer_support",
        inferred_capabilities=[
            Capability(name="Order Tracking", description="Track FedEx and UPS packages"),
            Capability(name="Refunds", description="Refund orders under $500")
        ],
        boundaries=["Never exceed $500 without supervisor approval"]
    )

    confirmed_spec = await forge_service.confirm_spec(spec)
    assert confirmed_spec.confirmed is True

    blueprint = await forge_service.assemble_blueprint(confirmed_spec)
    assert blueprint.review_required is False
    assert len(blueprint.review_flags) == 0
