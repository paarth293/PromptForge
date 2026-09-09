import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.db.session import DB_PATH
from backend.app.main import app


@pytest.mark.asyncio
async def test_api_forge_decompose_endpoint():
    await run_migrations(DB_PATH)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/forge/decompose",
            headers={"X-Tenant-ID": "tenant-sales-team"},
            json={"description": "Build me a lead qualification agent for my sales team."}
        )
        assert response.status_code == 200
        spec_data = response.json()
        assert spec_data["spec_id"] is not None
        assert spec_data["tenant_id"] == "tenant-sales-team"
        assert len(spec_data["inferred_capabilities"]) > 0

        # Verify persisted in database
        repo = PipelineRepository(DB_PATH)
        persisted = await repo.get_spec(spec_data["spec_id"])
        assert persisted is not None
        assert persisted.spec_id == spec_data["spec_id"]
        assert persisted.tenant_id == "tenant-sales-team"
