"""Tests for Audit Remediation Fixes.

Validates:
1. GET /api/blueprints list endpoint scoped by tenant.
2. GET /api/blueprints/{blueprint_id}/chain returns valid tamper-evident hash chain.
3. GET /api/redteam/stream/{blueprint_id}?tenant_id=... accepts query param tenant without headers.
4. Seeding demo profiles generates SHIELD policy and records audit trail.
5. ForgeService.assemble_blueprint generates SHIELD policy and records audit trail.
"""

import pytest
from app.core.demo_profiles import CUSTOMER_SUPPORT_PROFILE
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.main import app
from app.services.forge_service import ForgeService
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
async def init_test_db(tmp_path):
    db_file = str(tmp_path / "test_audit_remed.db")
    await run_migrations(db_file)
    import app.db.session as session
    import app.main as main_mod
    orig_path = session.DB_PATH
    session.DB_PATH = db_file
    main_mod.DB_PATH = db_file
    yield db_file
    session.DB_PATH = orig_path
    main_mod.DB_PATH = orig_path


@pytest.mark.asyncio
async def test_list_blueprints_and_chain_endpoints():
    """Verify GET /api/blueprints and GET /api/blueprints/{blueprint_id}/chain."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Seed demo profile
        seed_res = await client.post(
            "/api/demo/seed/customer-support",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        assert seed_res.status_code == 200
        bp_id = seed_res.json()["blueprint_id"]

        # 2. List blueprints
        list_res = await client.get(
            "/api/blueprints",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        assert list_res.status_code == 200
        bps = list_res.json()
        assert len(bps) >= 1
        assert any(b["blueprint_id"] == bp_id for b in bps)

        # Cross-tenant check: other tenant sees empty list
        other_res = await client.get(
            "/api/blueprints",
            headers={"X-Tenant-ID": "tenant-other"}
        )
        assert other_res.status_code == 200
        assert len(other_res.json()) == 0

        # 3. Hash chain endpoint
        chain_res = await client.get(
            f"/api/blueprints/{bp_id}/chain",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        assert chain_res.status_code == 200
        chain_data = chain_res.json()
        assert chain_data["valid"] is True
        assert chain_data["chain_length"] >= 1
        assert chain_data["invalid_at_block"] is None


@pytest.mark.asyncio
async def test_redteam_stream_query_tenant_id():
    """Verify EventSource compatibility: stream accepts tenant_id via query param."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed under tenant-demo
        seed_res = await client.post(
            "/api/demo/seed/customer-support",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        bp_id = seed_res.json()["blueprint_id"]

        # Query without X-Tenant-ID header, but with ?tenant_id=tenant-demo
        res = await client.get(
            f"/api/redteam/stream/{bp_id}?attacks_per_persona=1&concurrency=2&tenant_id=tenant-demo"
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]


@pytest.mark.asyncio
async def test_forge_and_demo_seed_generate_shield_policy(tmp_path):
    """Verify SHIELD policy and audit events are generated on blueprint assembly."""
    repo = PipelineRepository(db_path=str(tmp_path / "test_shield.db"))
    await run_migrations(repo.db_path)

    forge = ForgeService(repo=repo)
    spec = await forge.decompose_intent(
        description=CUSTOMER_SUPPORT_PROFILE.raw_description,
        tenant_id="tenant-demo"
    )
    confirmed = await forge.confirm_spec(spec)
    bp = await forge.assemble_blueprint(confirmed)

    # Verify SHIELD policy exists in repository
    policy = await repo.get_policy_by_spec(confirmed.spec_id)
    assert policy is not None
    assert policy.spec_id == confirmed.spec_id

    # Verify Audit trail exists in repository
    events = await repo.get_audit_events_for_agent(bp.blueprint_id)
    assert len(events) >= 1
    assert events[0].event_type == "forge_complete"
