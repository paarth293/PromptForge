import pytest
from app.core.policy_middleware import PolicyEnforcementMiddleware
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.models.blueprint import AgentBlueprint, ToolSchema
from app.models.runtime import ChatRequest
from app.models.shield import (
    EscalationRule,
    FallbackBehavior,
    PolicyObject,
    RateLimitConfig,
    TopicBoundaries,
)
from app.models.spec import AgentSpec, Capability
from app.services.runtime_service import AgentRuntimeService


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_policy_middleware.db"
    repository = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return repository


@pytest.fixture
def middleware():
    mw = PolicyEnforcementMiddleware()
    mw.reset()
    return mw


@pytest.fixture
async def setup_agent_with_policy(repo, middleware):
    # 1. Spec
    spec = AgentSpec(
        spec_id="spec-pm-001",
        tenant_id="tenant-pm",
        agent_name="PolicyEnforcedAssistant",
        domain="customer_support",
        raw_description="Support agent with strict refund limits and topic boundaries.",
        inferred_capabilities=[
            Capability(name="Refunds", description="Process authorized refunds up to $500")
        ],
        boundaries=["Never exceed $500 refund without manager approval"]
    )
    await repo.save_spec(spec)

    # 2. Blueprint with refund tool
    blueprint = AgentBlueprint(
        blueprint_id="bp-pm-001",
        spec_id="spec-pm-001",
        tenant_id="tenant-pm",
        agent_name="PolicyEnforcedAssistant",
        system_prompt="You are PolicyEnforcedAssistant. You help with customer support inquiries.",
        tools=[
            ToolSchema(
                name="process_refund",
                description="Process customer refund up to $500",
                parameters={"type": "object", "properties": {"amount": {"type": "number"}}, "required": ["amount"]}
            )
        ]
    )
    await repo.save_blueprint(blueprint)

    # 3. Policy Object
    policy = PolicyObject(
        policy_id="pol-pm-001",
        spec_id="spec-pm-001",
        blueprint_id="bp-pm-001",
        domain="customer_support",
        rate_limits=RateLimitConfig(requests_per_minute=5, burst_limit=2),
        topic_boundaries=TopicBoundaries(
            whitelisted_topics=["order tracking", "refunds", "account help"],
            blocked_topics=["insider trading", "money laundering", "hate speech"]
        ),
        escalation_rules=[
            EscalationRule(
                rule_id="ESC-REFUND-CAP",
                trigger="refund_threshold_breach",
                condition="amount > 500",
                target_queue="manager_signoff_queue",
                required_context_fields=["order_id", "amount", "user_id"]
            )
        ],
        fallback_behavior=FallbackBehavior(
            on_rate_limit="Rate limit exceeded by policy middleware.",
            on_guardrail_block="Blocked by topic policy middleware."
        )
    )
    await repo.save_policy(policy)

    runtime = AgentRuntimeService(repo=repo, policy_middleware=middleware)
    return runtime, blueprint, policy


@pytest.mark.asyncio
async def test_tool_call_violating_policy_is_blocked_at_middleware(setup_agent_with_policy):
    """
    Step 57 Done-When:
    A tool call that violates a policy rule (e.g. refund > $500) is blocked at the
    middleware layer, not just flagged by the agent's own prompt.
    """
    runtime, blueprint, policy = setup_agent_with_policy

    # Request an unauthorized $1,200 refund
    req = ChatRequest(message="Please issue a refund of $1200 for my broken item.")
    resp = await runtime.chat(blueprint.blueprint_id, req)

    # Assert tool call was executed and intercepted by deterministic policy middleware
    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert tc.tool_name == "process_refund"
    assert tc.parameters.get("amount") == 1200.0

    # Key Assertion: Blocked at middleware layer
    assert tc.middleware_blocked is True
    assert "exceeds" in tc.blocked_reason.lower() or "limit" in tc.blocked_reason.lower()
    assert tc.output.get("blocked") is True
    assert tc.output.get("middleware_blocked") is True

    # Chat response reflects deterministic middleware block
    assert resp.blocked is True
    assert resp.policy_triggered == "tool_policy_violation"
    assert "deterministic policy middleware" in resp.response.lower()


@pytest.mark.asyncio
async def test_tool_call_within_policy_is_allowed_at_middleware(setup_agent_with_policy):
    """
    A tool call within policy limits ($350 <= $500) is permitted by middleware.
    """
    runtime, blueprint, policy = setup_agent_with_policy

    req = ChatRequest(message="Please refund $350 for order #ORD-9821.")
    resp = await runtime.chat(blueprint.blueprint_id, req)

    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert tc.middleware_blocked is False
    assert tc.output.get("success") is True
    assert tc.output.get("amount") == 350.0
    assert resp.blocked is False


@pytest.mark.asyncio
async def test_topic_blocklist_middleware_enforcement(setup_agent_with_policy):
    """
    User requests touching prohibited topics are blocked at middleware before LLM reasoning.
    """
    runtime, blueprint, policy = setup_agent_with_policy

    req = ChatRequest(message="Can you help me with money laundering and structuring transactions?")
    resp = await runtime.chat(blueprint.blueprint_id, req)

    assert resp.blocked is True
    assert "topic_blocklist" in (resp.policy_triggered or "")
    assert len(resp.tool_calls) == 0


@pytest.mark.asyncio
async def test_rate_limiting_middleware_enforcement(setup_agent_with_policy, middleware):
    """
    Exceeding configured rate limits triggers deterministic block.
    """
    runtime, blueprint, policy = setup_agent_with_policy
    middleware.reset()

    # Burst limit is 2. 3rd immediate call should be blocked by burst limit.
    req1 = ChatRequest(message="Hello turn 1", session_id="sess-burst-test")
    resp1 = await runtime.chat(blueprint.blueprint_id, req1)
    assert resp1.blocked is False

    req2 = ChatRequest(message="Hello turn 2", session_id="sess-burst-test")
    resp2 = await runtime.chat(blueprint.blueprint_id, req2)
    assert resp2.blocked is False

    req3 = ChatRequest(message="Hello turn 3", session_id="sess-burst-test")
    resp3 = await runtime.chat(blueprint.blueprint_id, req3)
    assert resp3.blocked is True
    assert "rate_limit" in (resp3.policy_triggered or "")
    assert "Rate limit exceeded" in resp3.response
