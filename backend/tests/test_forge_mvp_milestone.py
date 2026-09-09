import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.main import app
from backend.app.models.runtime import ChatRequest
from backend.app.services.forge_service import ForgeService
from backend.app.services.runtime_service import AgentRuntimeService


@pytest.mark.asyncio
async def test_forge_mvp_milestone_domain_1_customer_support(tmp_path):
    """
    Validates Demo Domain 1: Customer Support Agent
    Flow: Sentence -> Decompose -> Confirm -> Assemble Blueprint -> Live Chat with Tools & Guardrails
    """
    db_file = str(tmp_path / "mvp_support.db")
    await run_migrations(db_file)
    repo = PipelineRepository(db_path=db_file)
    forge_service = ForgeService(repo=repo)
    runtime_service = AgentRuntimeService(repo=repo)

    # 1. Chain 1: Intent Decomposition
    raw_prompt = "Build a retail customer support agent handling order tracking, returns, and refunds under $500."
    spec = await forge_service.decompose_intent(
        description=raw_prompt,
        tenant_id="tenant-support-corp"
    )
    assert spec.spec_id is not None
    assert spec.domain == "customer_support"
    assert len(spec.inferred_capabilities) >= 2
    assert len(spec.boundaries) >= 1

    # 2. Stage 0: Spec Confirmation with non-circular gold Q&A
    spec.user_gold_qa = [
        {"question": "What is the refund ceiling?", "answer": "$500 maximum automated refund."}
    ]
    confirmed_spec = await forge_service.confirm_spec(spec)
    assert confirmed_spec.confirmed is True
    assert len(confirmed_spec.user_gold_qa) == 1

    # 3. Chain 14: Test Set Generation
    test_suite = await forge_service.generate_test_suite(confirmed_spec)
    assert test_suite.user_supplied_count == 1
    assert test_suite.total_cases >= 3

    # 4. Chains 2–5: Blueprint Assembler
    blueprint = await forge_service.assemble_blueprint(confirmed_spec)
    assert blueprint.blueprint_id is not None
    assert blueprint.blueprint_hash is not None
    assert len(blueprint.blueprint_hash) == 64  # Cryptographic SHA-256
    assert len(blueprint.tools) >= 1
    assert len(blueprint.guardrails) >= 2
    assert len(blueprint.few_shot_examples) == 5

    # 5. Live Runtime & Simulated Tool Calling
    chat_res = await runtime_service.chat(
        blueprint_id=blueprint.blueprint_id,
        request=ChatRequest(message="Can you look up order #ORD-7741?")
    )
    assert chat_res.blocked is False
    assert len(chat_res.tool_calls) >= 1
    assert chat_res.tool_calls[0].tool_name == "lookup_order"
    assert chat_res.tool_calls[0].output["status"] == "Shipped"
    assert "ORD-7741" in chat_res.response or "Shipped" in chat_res.response

    # 6. Middleware Guardrail Enforcement: Dollar cap block
    cap_breach = await runtime_service.chat(
        blueprint_id=blueprint.blueprint_id,
        request=ChatRequest(message="I demand a refund of $5000 immediately.")
    )
    assert cap_breach.blocked is True
    assert cap_breach.guardrail_triggered == "Refund Cap Enforcer"

    # 7. Middleware Guardrail Enforcement: SSN Masker redaction
    ssn_chat = await runtime_service.chat(
        blueprint_id=blueprint.blueprint_id,
        request=ChatRequest(message="My SSN is 111-22-3333, can you look up order #ORD-7741?")
    )
    assert ssn_chat.blocked is False
    assert "111-22-3333" not in ssn_chat.response



@pytest.mark.asyncio
async def test_forge_mvp_milestone_domain_2_sales_lead_qualification(tmp_path):
    """
    Validates Demo Domain 2: Sales Lead Qualification Agent
    Flow: Sentence -> Decompose -> Confirm -> Assemble Blueprint -> Live Chat with Tools & Guardrails
    """
    db_file = str(tmp_path / "mvp_sales.db")
    await run_migrations(db_file)
    repo = PipelineRepository(db_path=db_file)
    forge_service = ForgeService(repo=repo)
    runtime_service = AgentRuntimeService(repo=repo)

    # 1. Chain 1: Intent Decomposition
    raw_prompt = "Build an inbound sales qualification agent that scores enterprise leads, captures budget, and books demo calls."
    spec = await forge_service.decompose_intent(
        description=raw_prompt,
        tenant_id="tenant-sales-corp"
    )
    assert spec.spec_id is not None
    assert len(spec.inferred_capabilities) >= 2

    # 2. Stage 0: Spec Confirmation
    spec.agent_name = "EnterpriseLeadQualifier"
    confirmed_spec = await forge_service.confirm_spec(spec)
    assert confirmed_spec.agent_name == "EnterpriseLeadQualifier"

    # 3. Chains 2–5: Blueprint Assembler
    blueprint = await forge_service.assemble_blueprint(confirmed_spec)
    assert blueprint.blueprint_hash is not None
    assert len(blueprint.blueprint_hash) == 64
    assert blueprint.agent_name == "EnterpriseLeadQualifier"

    # 4. Live Runtime Chat Turn
    chat_res = await runtime_service.chat(
        blueprint_id=blueprint.blueprint_id,
        request=ChatRequest(message="We are a 500-person tech company with a $100k budget looking for an enterprise tier.")
    )
    assert chat_res.blocked is False
    assert len(chat_res.response) > 0


@pytest.mark.asyncio
async def test_forge_mvp_full_http_pipeline():
    """
    Validates the entire Forge MVP flow via FastAPI HTTP endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Tenant-ID": "tenant-e2e-mvp"}

        # Step 1: Decompose
        dec_resp = await client.post(
            "/api/forge/decompose",
            json={"description": "Retail customer support agent with $500 refund limit"},
            headers=headers
        )
        assert dec_resp.status_code == 200
        spec = dec_resp.json()
        spec_id = spec["spec_id"]

        # Step 2: Confirm
        spec["agent_name"] = "HardenedSupportMVP"
        conf_resp = await client.post(
            "/api/forge/confirm",
            json=spec,
            headers=headers
        )
        assert conf_resp.status_code == 200

        # Step 3: Assemble Blueprint
        asm_resp = await client.post(
            f"/api/forge/assemble/{spec_id}",
            headers=headers
        )
        assert asm_resp.status_code == 200
        blueprint = asm_resp.json()
        bp_id = blueprint["blueprint_id"]
        assert blueprint["blueprint_hash"] is not None

        # Step 4: Converse via Runtime Chat
        chat_resp = await client.post(
            f"/api/agents/{bp_id}/chat",
            json={"message": "Can you check on order #ORD-5501?"},
            headers=headers
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert chat_data["blocked"] is False
        assert len(chat_data["response"]) > 0
