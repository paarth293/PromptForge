import pytest
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.main import app
from app.models.blueprint import AgentBlueprint, Guardrail
from app.models.spec import AgentSpec, Capability
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_api_verify.db"
    return PipelineRepository(db_path=str(db_file))


@pytest.fixture
def test_spec():
    return AgentSpec(
        spec_id="spec-verify-api-001",
        tenant_id="tenant-demo",
        agent_name="RetailSupportBot",
        domain="customer_support",
        inferred_capabilities=[
            Capability(name="Refund Processing", description="Refund up to $500", confirmed=True),
            Capability(name="Order Lookup", description="Track orders", confirmed=True),
        ],
        boundaries=["Refund cap $500"],
        user_gold_qa=[
            {"question": "What is your refund limit?", "answer": "Our refund limit is $500."}
        ],
        confirmed=True,
    )


@pytest.fixture
def test_blueprint(test_spec):
    return AgentBlueprint(
        blueprint_id="bp-verify-api-001",
        spec_id=test_spec.spec_id,
        tenant_id="tenant-demo",
        agent_name="RetailSupportBot",
        system_prompt="You are RetailSupportBot. You assist customers with order tracking and refunds up to $500.",
        guardrails=[
            Guardrail(name="Refund Cap", layer="middleware", pattern_or_rule="amount <= 500", action="block")
        ],
    )


@pytest.mark.asyncio
async def test_verify_endpoints_lifecycle(test_spec, test_blueprint):
    """
    Tests POST /api/verify/run/{blueprint_id},
    GET /api/verify/scorecard/{blueprint_id},
    and GET /api/verify/scorecard/{blueprint_id}/formatted.
    """
    repo = PipelineRepository()
    await run_migrations(repo.db_path)
    await repo.save_spec(test_spec)
    await repo.save_blueprint(test_blueprint)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-Tenant-ID": "tenant-demo"}

        # 1. Run Verification
        run_res = await ac.post(f"/api/verify/run/{test_blueprint.blueprint_id}", headers=headers)
        assert run_res.status_code == 200
        card_data = run_res.json()

        assert card_data["blueprint_id"] == test_blueprint.blueprint_id
        assert card_data["promptforge_composite_score"] >= 0
        assert card_data["scorecard_hash"] is not None
        assert "weight" in card_data["formula_disclosed"] or "=" in card_data["formula_disclosed"]

        # 2. Get Scorecard
        get_res = await ac.get(f"/api/verify/scorecard/{test_blueprint.blueprint_id}", headers=headers)
        assert get_res.status_code == 200
        fetched = get_res.json()
        assert fetched["scorecard_id"] == card_data["scorecard_id"]
        assert fetched["promptforge_composite_score"] == card_data["promptforge_composite_score"]

        # 3. Get Formatted Scorecard
        fmt_res = await ac.get(f"/api/verify/scorecard/{test_blueprint.blueprint_id}/formatted", headers=headers)
        assert fmt_res.status_code == 200
        fmt_data = fmt_res.json()
        assert "PROMPTFORGE SCORECARD" in fmt_data["formatted_scorecard"]
        assert "PromptForge Score" in fmt_data["formatted_scorecard"]
