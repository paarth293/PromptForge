import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.db.session import DB_PATH
from backend.app.main import app


@pytest.mark.asyncio
async def test_spec_confirmation_flow():
    await run_migrations(DB_PATH)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Decompose intent
        dec_res = await client.post(
            "/api/forge/decompose",
            headers={"X-Tenant-ID": "tenant-support-dept"},
            json={"description": "Build me a support agent that handles refunds up to $500."}
        )
        assert dec_res.status_code == 200
        spec = dec_res.json()
        assert spec["confirmed"] is False

        # 2. User modifies capabilities and boundaries (Stage 0 correction)
        spec["inferred_capabilities"][0]["description"] = "User corrected: Only process refunds with verified invoice"
        spec["boundaries"].append("Never refund expired subscriptions")
        spec["user_gold_qa"] = [{"question": "What is maximum refund?", "answer": "$500"}]

        # 3. Confirm spec endpoint
        confirm_res = await client.post(
            "/api/forge/confirm",
            headers={"X-Tenant-ID": "tenant-support-dept"},
            json=spec
        )
        assert confirm_res.status_code == 200
        confirmed_spec = confirm_res.json()
        assert confirmed_spec["confirmed"] is True
        assert confirmed_spec["inferred_capabilities"][0]["description"] == "User corrected: Only process refunds with verified invoice"
        assert "Never refund expired subscriptions" in confirmed_spec["boundaries"]

        # 4. Verify persisted state in DB
        repo = PipelineRepository(DB_PATH)
        persisted = await repo.get_spec(spec["spec_id"])
        assert persisted is not None
        assert persisted.confirmed is True
        assert persisted.inferred_capabilities[0].description == "User corrected: Only process refunds with verified invoice"
        assert len(persisted.user_gold_qa) == 1
