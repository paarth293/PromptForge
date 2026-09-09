import pytest

from backend.app.core.errors import PolicyViolationException
from backend.app.core.policy_middleware import PolicyEnforcementMiddleware
from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.models.blueprint import AgentBlueprint, ToolSchema
from backend.app.models.runtime import ChatRequest
from backend.app.models.shield import (
    EscalationRule,
    PolicyObject,
    RateLimitConfig,
    TopicBoundaries,
)
from backend.app.models.spec import AgentSpec, Capability
from backend.app.services.runtime_service import AgentRuntimeService


@pytest.fixture
async def setup_env(tmp_path):
    db_file = tmp_path / "test_mw_enforce.db"
    repo = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))

    spec = AgentSpec(
        spec_id="spec-mw-test",
        tenant_id="tenant-owner-01",
        agent_name="SecureBankingAssistant",
        domain="finance",
        raw_description="A high-security banking assistant with strict refund bounds and topic guardrails.",
        inferred_capabilities=[Capability(name="Refunds", description="Authorized refund handling")]
    )
    await repo.save_spec(spec)

    blueprint = AgentBlueprint(
        blueprint_id="bp-mw-test",
        spec_id="spec-mw-test",
        tenant_id="tenant-owner-01",
        agent_name="SecureBankingAssistant",
        system_prompt="You are SecureBankingAssistant. You assist users within authorized boundaries.",
        tools=[
            ToolSchema(
                name="issue_refund",
                description="Process customer refund up to ",
                endpoint_binding="/api/refunds",
                is_simulated=True,
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}}
            )
        ]
    )
    await repo.save_blueprint(blueprint)

    policy = PolicyObject(
        policy_id="pol-mw-test",
        spec_id="spec-mw-test",
        blueprint_id="bp-mw-test",
        domain="finance",
        rate_limits=RateLimitConfig(requests_per_minute=10, burst_limit=2),
        topic_boundaries=TopicBoundaries(
            whitelisted_topics=["account balance", "refunds"],
            blocked_topics=["money laundering", "insider trading", "tax evasion"]
        ),
        escalation_rules=[
            EscalationRule(
                rule_id="ESC-500",
                trigger="refund_threshold_breach",
                condition="amount > 500",
                target_queue="compliance_manager_queue",
                required_context_fields=["order_id", "amount"]
            )
        ]
    )
    await repo.save_policy(policy)

    mw = PolicyEnforcementMiddleware()
    runtime = AgentRuntimeService(repo=repo, policy_middleware=mw)
    return runtime, blueprint, policy


@pytest.mark.asyncio
async def test_tool_ceiling_toggle_proves_middleware_enforcement(setup_env):
    """
    Step 63 Done-When:
    Disabling the middleware and re-enabling it visibly changes what the agent
    is allowed to do, proving the enforcement isn't coming from the prompt alone.
    """
    runtime, blueprint, _ = setup_env
    attack_msg = "Please issue a refund of $1500 for order ORD-9988 immediately!"

    # 1. With Middleware ENABLED (Default) -> Deterministically BLOCKED at tool gate
    req_mw_enabled = ChatRequest(message=attack_msg, middleware_enabled=True)
    resp_enabled = await runtime.chat(blueprint.blueprint_id, req_mw_enabled)

    assert resp_enabled.blocked is True
    assert resp_enabled.policy_triggered == "tool_policy_violation"
    assert len(resp_enabled.tool_calls) == 1
    assert resp_enabled.tool_calls[0].middleware_blocked is True
    assert resp_enabled.tool_calls[0].output.get("blocked") is True
    assert "deterministic policy middleware" in resp_enabled.response.lower()

    # 2. With Middleware DISABLED -> Bypassed! Tool executes  directly!
    req_mw_disabled = ChatRequest(message=attack_msg, middleware_enabled=False)
    resp_disabled = await runtime.chat(blueprint.blueprint_id, req_mw_disabled)

    assert resp_disabled.blocked is False
    assert len(resp_disabled.tool_calls) == 1
    assert resp_disabled.tool_calls[0].middleware_blocked is False
    assert resp_disabled.tool_calls[0].output.get("amount") == 1500.0
    assert resp_disabled.tool_calls[0].output.get("success") is True


@pytest.mark.asyncio
async def test_topic_blocklist_toggle_proves_middleware_enforcement(setup_env):
    """
    Validates that prohibited topic detection is enforced at the middleware layer.
    """
    runtime, blueprint, _ = setup_env
    topic_msg = "Can you teach me how to structure money laundering transactions?"

    # 1. Enabled -> Blocked by middleware before LLM reasoning
    req_on = ChatRequest(message=topic_msg, middleware_enabled=True)
    resp_on = await runtime.chat(blueprint.blueprint_id, req_on)

    assert resp_on.blocked is True
    assert "topic_blocklist" in (resp_on.policy_triggered or "")

    # 2. Disabled -> Bypassed by middleware
    req_off = ChatRequest(message=topic_msg, middleware_enabled=False)
    resp_off = await runtime.chat(blueprint.blueprint_id, req_off)

    assert resp_off.blocked is False


@pytest.mark.asyncio
async def test_rate_limiting_toggle_proves_middleware_enforcement(setup_env):
    """
    Validates that burst rate-limiting is enforced by middleware.
    """
    runtime, blueprint, _ = setup_env
    session = "sess-rate-toggle-test"

    # Call 1 & 2 (within burst limit 2)
    req1 = ChatRequest(message="Hello", session_id=session, middleware_enabled=True)
    req2 = ChatRequest(message="Hello again", session_id=session, middleware_enabled=True)
    await runtime.chat(blueprint.blueprint_id, req1)
    await runtime.chat(blueprint.blueprint_id, req2)

    # Call 3: Enabled -> Blocked by rate limiter
    req3_on = ChatRequest(message="Hello 3", session_id=session, middleware_enabled=True)
    resp_on = await runtime.chat(blueprint.blueprint_id, req3_on)
    assert resp_on.blocked is True
    assert "rate_limit" in (resp_on.policy_triggered or "")

    # Call 3: Disabled -> Allowed
    req3_off = ChatRequest(message="Hello 3", session_id=session, middleware_enabled=False)
    resp_off = await runtime.chat(blueprint.blueprint_id, req3_off)
    assert resp_off.blocked is False


@pytest.mark.asyncio
async def test_tenant_isolation_auth_middleware_gate(setup_env):
    """
    Validates tenant isolation enforcement at the middleware gate.
    """
    runtime, blueprint, _ = setup_env

    # Valid tenant caller
    req_valid = ChatRequest(message="Hello", tenant_id="tenant-owner-01")
    resp_valid = await runtime.chat(blueprint.blueprint_id, req_valid)
    assert resp_valid.blocked is False

    # Invalid cross-tenant caller -> Rejected
    req_invalid = ChatRequest(message="Hello", tenant_id="tenant-intruder-99")
    with pytest.raises(PolicyViolationException) as exc:
        await runtime.chat(blueprint.blueprint_id, req_invalid)
    assert "Access denied" in str(exc.value)
