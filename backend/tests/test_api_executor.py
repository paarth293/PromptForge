import json

import httpx
import pytest

from backend.app.core.api_executor import (
    ApiExecutionRequest,
    ApiExecutor,
)
from backend.app.core.policy_middleware import PolicyEnforcementMiddleware
from backend.app.db.repository import PipelineRepository
from backend.app.models.blueprint import AgentBlueprint, ToolSchema
from backend.app.models.runtime import ChatRequest
from backend.app.models.shield import EscalationRule, PolicyObject, RateLimitConfig, TopicBoundaries
from backend.app.models.spec import AgentSpec, Capability
from backend.app.services.runtime_service import AgentRuntimeService


@pytest.mark.asyncio
async def test_api_executor_ssrf_and_allowlist_enforcement():
    executor = ApiExecutor(allowed_domains=["httpbin.org", "api.stripe.com"])

    # 1. Scheme check
    res_ftp = await executor.call_api(ApiExecutionRequest(url="ftp://httpbin.org/resource"))
    assert res_ftp.success is False
    assert res_ftp.status_code == 403
    assert "Unsupported URL scheme" in (res_ftp.error or "")

    # 2. Localhost SSRF
    res_local = await executor.call_api(ApiExecutionRequest(url="http://localhost:8000/internal"))
    assert res_local.success is False
    assert res_local.status_code == 403
    assert "SSRF Protection" in (res_local.error or "")

    # 3. Private IP SSRF
    res_ip = await executor.call_api(ApiExecutionRequest(url="http://192.168.1.1/admin"))
    assert res_ip.success is False
    assert res_ip.status_code == 403
    assert "SSRF Protection" in (res_ip.error or "")

    # 4. AWS Metadata SSRF
    res_meta = await executor.call_api(ApiExecutionRequest(url="http://169.254.169.254/latest/meta-data/"))
    assert res_meta.success is False
    assert res_meta.status_code == 403
    assert "SSRF Protection" in (res_meta.error or "")

    # 5. Non-allowlisted domain
    res_evil = await executor.call_api(ApiExecutionRequest(url="https://attacker-domain.com/leak"))
    assert res_evil.success is False
    assert res_evil.status_code == 403
    assert "not in the allowed API domain registry" in (res_evil.error or "")


@pytest.mark.asyncio
async def test_api_executor_mock_http_execution():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://httpbin.org/post"
        assert request.headers.get("User-Agent") == "PromptForge-AgentRuntime/1.0"
        body = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            status_code=200,
            json={"status": "success", "echoed_body": body, "id": "tx_9981"}
        )

    transport = httpx.MockTransport(mock_handler)
    executor = ApiExecutor(allowed_domains=["httpbin.org"], transport=transport)

    req = ApiExecutionRequest(
        url="https://httpbin.org/post",
        method="POST",
        json_body={"order_id": "ORD-123", "amount": 99.50}
    )
    res = await executor.call_api(req)

    assert res.success is True
    assert res.status_code == 200
    assert res.response_data["status"] == "success"
    assert res.response_data["id"] == "tx_9981"
    assert res.response_data["echoed_body"]["amount"] == 99.50
    assert res.execution_duration_ms >= 0.0


@pytest.mark.asyncio
async def test_api_executor_http_error_handling():
    def not_found_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=404,
            json={"error": "Resource not found"}
        )

    transport = httpx.MockTransport(not_found_handler)
    executor = ApiExecutor(allowed_domains=["httpbin.org"], transport=transport)

    req = ApiExecutionRequest(url="https://httpbin.org/orders/missing", method="GET")
    res = await executor.call_api(req)

    assert res.success is False
    assert res.status_code == 404
    assert "HTTP 404" in (res.error or "")


@pytest.mark.asyncio
async def test_runtime_service_real_api_tool_integration(tmp_path):
    # Setup mock transport for sandbox endpoint
    def sandbox_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8")) if request.content else {}
        return httpx.Response(
            status_code=200,
            json={
                "status": "processed",
                "refund_id": "re_live_stripe_test",
                "amount": body.get("amount", 0.0),
                "order_id": body.get("order_id")
            }
        )

    transport = httpx.MockTransport(sandbox_handler)
    executor = ApiExecutor(allowed_domains=["httpbin.org", "api.stripe.com"], transport=transport)

    db_file = tmp_path / "test_api_runtime.db"
    repo = PipelineRepository(db_path=str(db_file))
    from backend.app.db.migrator import run_migrations
    await run_migrations(str(db_file))

    runtime = AgentRuntimeService(repo=repo, api_executor=executor)

    spec = AgentSpec(
        spec_id="spec-live-api-01",
        tenant_id="tenant-default",
        agent_name="LiveStripeSupportAgent",
        domain="customer_support",
        raw_description="Support agent with live Stripe tool integration",
        inferred_capabilities=[Capability(name="Refunds", description="Issue refunds")]
    )
    await repo.save_spec(spec)

    blueprint = AgentBlueprint(
        blueprint_id="bp-live-api-01",
        spec_id="spec-live-api-01",
        agent_name="LiveStripeSupportAgent",
        system_prompt="You are LiveStripeSupportAgent. Process customer refunds reliably.",
        tools=[
            ToolSchema(
                name="issue_refund",
                description="Process real customer refund",
                endpoint_binding="https://httpbin.org/post",
                is_simulated=False,
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}}
            )
        ]
    )
    await repo.save_blueprint(blueprint)

    # Chat execution invoking the live API tool
    chat_req = ChatRequest(message="Please issue a refund of $85.00 for order ORD-9988.")
    resp = await runtime.chat(blueprint.blueprint_id, chat_req)

    assert resp.blocked is False
    assert len(resp.tool_calls) == 1
    tool_call = resp.tool_calls[0]
    assert tool_call.tool_name == "issue_refund"
    assert tool_call.is_live_call is True
    assert tool_call.http_status == 200
    assert tool_call.output.get("status") == "processed"
    assert tool_call.output.get("refund_id") == "re_live_stripe_test"
    assert tool_call.output.get("amount") == 85.0
    assert tool_call.parameters.get("order_id") == "ORD-9988"


@pytest.mark.asyncio
async def test_runtime_service_real_api_tool_blocked_by_policy_before_dispatch(tmp_path):
    network_dispatched = False

    def should_not_be_called(request: httpx.Request) -> httpx.Response:
        nonlocal network_dispatched
        network_dispatched = True
        return httpx.Response(status_code=200, json={"status": "unexpected_success"})

    transport = httpx.MockTransport(should_not_be_called)
    executor = ApiExecutor(allowed_domains=["httpbin.org"], transport=transport)

    db_file = tmp_path / "test_api_blocked.db"
    repo = PipelineRepository(db_path=str(db_file))
    from backend.app.db.migrator import run_migrations
    await run_migrations(str(db_file))

    middleware = PolicyEnforcementMiddleware()
    runtime = AgentRuntimeService(repo=repo, policy_middleware=middleware, api_executor=executor)

    spec = AgentSpec(
        spec_id="spec-live-api-blocked",
        tenant_id="tenant-default",
        agent_name="StrictSupportAgent",
        domain="customer_support",
        raw_description="Support agent with strict refund limits",
        inferred_capabilities=[Capability(name="Refunds", description="Issue refunds")]
    )
    await repo.save_spec(spec)

    blueprint = AgentBlueprint(
        blueprint_id="bp-live-api-blocked",
        spec_id="spec-live-api-blocked",
        agent_name="StrictSupportAgent",
        system_prompt="You are StrictSupportAgent.",
        tools=[
            ToolSchema(
                name="issue_refund",
                description="Process customer refund",
                endpoint_binding="https://httpbin.org/post",
                is_simulated=False,
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}}
            )
        ]
    )
    await repo.save_blueprint(blueprint)

    # Attach strict policy: refund >  requires human manager
    policy = PolicyObject(
        policy_id="pol-strict-01",
        spec_id="spec-live-api-blocked",
        blueprint_id="bp-live-api-blocked",
        domain="customer_support",
        rate_limits=RateLimitConfig(requests_per_minute=10, burst_limit=5),
        topic_boundaries=TopicBoundaries(whitelisted_topics=["refunds"], blocked_topics=[]),
        escalation_rules=[
            EscalationRule(
                rule_id="ESC-500",
                trigger="refund_threshold_breach",
                condition="amount > 500",
                target_queue="manager_signoff_queue",
                required_context_fields=["order_id", "amount"]
            )
        ]
    )
    await repo.save_policy(policy)

    # User attempts unauthorized  refund
    chat_req = ChatRequest(message="I demand a refund of  for order ORD-9988 immediately!")
    resp = await runtime.chat(blueprint.blueprint_id, chat_req)

    # Must be blocked by deterministic policy middleware BEFORE dispatch
    assert network_dispatched is False, "External network call was dispatched despite policy violation!"
    assert resp.blocked is True
    assert resp.policy_triggered == "tool_policy_violation"
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].middleware_blocked is True
    assert "deterministic policy middleware" in resp.response.lower()
