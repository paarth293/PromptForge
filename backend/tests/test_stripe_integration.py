import httpx
import pytest

from backend.app.core.api_executor import ApiExecutor
from backend.app.core.policy_middleware import PolicyEnforcementMiddleware
from backend.app.core.stripe_tool import StripeRefundAdapter
from backend.app.db.repository import PipelineRepository
from backend.app.models.blueprint import AgentBlueprint, ToolSchema
from backend.app.models.runtime import ChatRequest
from backend.app.models.shield import EscalationRule, PolicyObject, RateLimitConfig, TopicBoundaries
from backend.app.models.spec import AgentSpec, Capability
from backend.app.services.runtime_service import AgentRuntimeService


@pytest.mark.asyncio
async def test_stripe_adapter_test_mode_fixture():
    adapter = StripeRefundAdapter(api_key="")
    result = await adapter.execute_refund(
        amount_dollars=125.0,
        order_id="ORD-7762",
        reason="customer_return"
    )

    assert result["success"] is True
    assert result["live_mode"] is False
    assert result["stripe_refund_id"].startswith("re_test_")
    assert result["amount"] == 125.0
    assert result["amount_cents"] == 12500
    assert result["currency"] == "usd"
    assert result["order_id"] == "ORD-7762"
    assert result["status"] == "succeeded"


@pytest.mark.asyncio
async def test_stripe_adapter_with_test_api_key_and_mock_transport():
    called = False

    def stripe_mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        assert str(request.url).startswith("https://api.stripe.com/v1/refunds")
        assert request.headers.get("Authorization") == "Bearer sk_test_mock_123456789"
        return httpx.Response(
            status_code=200,
            json={
                "id": "re_3N99MockStripe123",
                "object": "refund",
                "amount": 20000,
                "currency": "usd",
                "status": "succeeded",
                "created": 1726000000
            }
        )

    transport = httpx.MockTransport(stripe_mock_handler)
    executor = ApiExecutor(allowed_domains=["api.stripe.com"], transport=transport)
    adapter = StripeRefundAdapter(api_executor=executor, api_key="sk_test_mock_123456789")

    result = await adapter.execute_refund(
        amount_dollars=200.0,
        order_id="ORD-1002"
    )

    assert called is True
    assert result["success"] is True
    assert result["stripe_refund_id"] == "re_3N99MockStripe123"
    assert result["status"] == "succeeded"
    assert result["amount"] == 200.0
    assert result["amount_cents"] == 20000


@pytest.mark.asyncio
async def test_runtime_agent_chat_with_stripe_refund_tool(tmp_path):
    db_file = tmp_path / "test_stripe_runtime.db"
    repo = PipelineRepository(db_path=str(db_file))
    from backend.app.db.migrator import run_migrations
    await run_migrations(str(db_file))

    adapter = StripeRefundAdapter(api_key="")
    runtime = AgentRuntimeService(repo=repo, stripe_adapter=adapter)

    spec = AgentSpec(
        spec_id="spec-stripe-demo-01",
        tenant_id="tenant-stripe-demo",
        agent_name="RetailNovaSupport",
        domain="customer_support",
        raw_description="Support agent with Stripe test-mode refund integration",
        inferred_capabilities=[Capability(name="Refunds", description="Stripe refunds")]
    )
    await repo.save_spec(spec)

    blueprint = AgentBlueprint(
        blueprint_id="bp-stripe-demo-01",
        spec_id="spec-stripe-demo-01",
        agent_name="RetailNovaSupport",
        system_prompt="You are RetailNovaSupport. Process customer refunds via Stripe.",
        tools=[
            ToolSchema(
                name="process_refund",
                description="Process real Stripe customer refund",
                endpoint_binding="https://api.stripe.com/v1/refunds",
                is_simulated=False,
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}}
            )
        ]
    )
    await repo.save_blueprint(blueprint)

    # Chat execution invoking the Stripe test-mode tool
    chat_req = ChatRequest(message="Please issue a refund of $75.00 for order ORD-4455.")
    resp = await runtime.chat(blueprint.blueprint_id, chat_req)

    assert resp.blocked is False
    assert len(resp.tool_calls) == 1
    tool_call = resp.tool_calls[0]
    assert tool_call.tool_name == "process_refund"
    assert tool_call.is_live_call is True
    assert tool_call.output.get("stripe_refund_id") is not None
    assert tool_call.output.get("stripe_refund_id").startswith("re_test_")
    assert tool_call.output.get("status") == "succeeded"
    assert tool_call.output.get("amount") == 75.0
    assert tool_call.output.get("amount_cents") == 7500


@pytest.mark.asyncio
async def test_runtime_agent_stripe_refund_policy_block(tmp_path):
    db_file = tmp_path / "test_stripe_policy_block.db"
    repo = PipelineRepository(db_path=str(db_file))
    from backend.app.db.migrator import run_migrations
    await run_migrations(str(db_file))

    middleware = PolicyEnforcementMiddleware()
    runtime = AgentRuntimeService(repo=repo, policy_middleware=middleware)

    spec = AgentSpec(
        spec_id="spec-stripe-block-01",
        tenant_id="tenant-stripe-demo",
        agent_name="RetailNovaSupport",
        domain="customer_support",
        raw_description="Support agent with Stripe test-mode refund integration and strict policy",
        inferred_capabilities=[Capability(name="Refunds", description="Stripe refunds")]
    )
    await repo.save_spec(spec)

    blueprint = AgentBlueprint(
        blueprint_id="bp-stripe-block-01",
        spec_id="spec-stripe-block-01",
        agent_name="RetailNovaSupport",
        system_prompt="You are RetailNovaSupport.",
        tools=[
            ToolSchema(
                name="process_refund",
                description="Process real Stripe customer refund",
                endpoint_binding="https://api.stripe.com/v1/refunds",
                is_simulated=False,
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}}
            )
        ]
    )
    await repo.save_blueprint(blueprint)

    # Attach policy cap at
    policy = PolicyObject(
        policy_id="pol-stripe-cap-01",
        spec_id="spec-stripe-block-01",
        blueprint_id="bp-stripe-block-01",
        domain="customer_support",
        rate_limits=RateLimitConfig(requests_per_minute=10, burst_limit=5),
        topic_boundaries=TopicBoundaries(whitelisted_topics=["refunds"], blocked_topics=[]),
        escalation_rules=[
            EscalationRule(
                rule_id="ESC-STRIPE-500",
                trigger="refund_threshold_breach",
                condition="amount > 500",
                target_queue="manager_signoff_queue",
                required_context_fields=["order_id", "amount"]
            )
        ]
    )
    await repo.save_policy(policy)

    # User attempts unauthorized  refund
    chat_req = ChatRequest(message="I demand a refund of $1200 for order ORD-4455 immediately!")
    resp = await runtime.chat(blueprint.blueprint_id, chat_req)

    assert resp.blocked is True
    assert resp.policy_triggered == "tool_policy_violation"
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].middleware_blocked is True
    assert "deterministic policy middleware" in resp.response.lower()
