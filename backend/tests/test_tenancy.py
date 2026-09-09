import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.migrator import run_migrations
from backend.app.db.session import DB_PATH
from backend.app.main import app


@pytest.mark.asyncio
async def test_tenant_isolation_api():
    await run_migrations(DB_PATH)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 0. Create a spec as Tenant A
        spec_res = await client.post(
            "/api/specs",
            headers={"X-Tenant-ID": "tenant-corp-a"},
            json={
                "spec_id": "spec-corp-a-01",
                "raw_description": "Support assistant description",
                "agent_name": "CorpA_Agent",
                "domain": "customer_support"
            }
        )
        assert spec_res.status_code == 200

        # 1. Create a blueprint as Tenant A referencing that spec
        create_res = await client.post(
            "/api/blueprints",
            headers={"X-Tenant-ID": "tenant-corp-a"},
            json={
                "spec_id": "spec-corp-a-01",
                "agent_name": "CorpA_Agent",
                "system_prompt": "Confidential Corp A System Instructions"
            }
        )
        assert create_res.status_code == 200
        bp_id = create_res.json()["blueprint_id"]
        assert create_res.json()["tenant_id"] == "tenant-corp-a"

        # 2. Fetch as Tenant A -> Allowed (200)
        fetch_a = await client.get(
            f"/api/blueprints/{bp_id}",
            headers={"X-Tenant-ID": "tenant-corp-a"}
        )
        assert fetch_a.status_code == 200
        assert fetch_a.json()["agent_name"] == "CorpA_Agent"

        # 3. Fetch as Tenant B -> Access Denied (403 PolicyViolationException)
        fetch_b = await client.get(
            f"/api/blueprints/{bp_id}",
            headers={"X-Tenant-ID": "tenant-rival-b"}
        )
        assert fetch_b.status_code == 403
        err_data = fetch_b.json()
        assert err_data["success"] is False
        assert err_data["error"]["code"] == "POLICY_VIOLATION"
        assert "tenant-corp-a" in err_data["error"]["message"]
