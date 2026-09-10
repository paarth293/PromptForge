"""Tests for Step 106: Customer Support and Lead Qualification Demo Profiles.

Confirms:
- Full specifications, boundaries, gold QA benchmarks, and tools for both demo profiles.
- Conversion to executable AgentSpec and AgentBlueprint.
- Zero-friction demo seeding endpoint for live presentation.
"""

import pytest
from app.core.demo_profiles import (
    CUSTOMER_SUPPORT_PROFILE,
    LEAD_QUALIFIER_PROFILE,
    get_all_demo_profiles,
    get_demo_profile,
)
from app.db.migrator import run_migrations
from app.main import app
from httpx import ASGITransport, AsyncClient


def test_customer_support_profile_invariants():
    """Verify Customer Support demo profile structure and boundaries."""
    p = CUSTOMER_SUPPORT_PROFILE
    assert p.profile_id == "customer-support"
    assert p.domain == "retail"
    assert len(p.inferred_capabilities) >= 3
    assert any(c.name == "process_refund" for c in p.inferred_capabilities)
    assert any(c.name == "check_order_status" for c in p.inferred_capabilities)
    assert any("500" in b for b in p.boundaries)
    assert len(p.user_gold_qa) >= 3
    assert len(p.tools) >= 3
    assert len(p.guardrails) >= 3

    # Check blueprint generation
    bp = p.to_blueprint(tenant_id="tenant-demo")
    assert bp.agent_name == p.agent_name
    assert "Strict Boundary:" in bp.system_prompt
    assert len(bp.tools) == len(p.tools)


def test_lead_qualifier_profile_invariants():
    """Verify Sales Lead Qualifier demo profile structure and boundaries."""
    p = LEAD_QUALIFIER_PROFILE
    assert p.profile_id == "lead-qualifier"
    assert p.domain == "b2b_saas"
    assert len(p.inferred_capabilities) >= 3
    assert any(c.name == "score_lead" for c in p.inferred_capabilities)
    assert any(c.name == "book_calendar_demo" for c in p.inferred_capabilities)
    assert any("discount" in b.lower() for b in p.boundaries)
    assert len(p.user_gold_qa) >= 3
    assert len(p.tools) >= 3
    assert len(p.guardrails) >= 3

    # Check spec generation
    spec = p.to_spec(tenant_id="tenant-demo")
    assert spec.agent_name == p.agent_name
    assert spec.confirmed is True


def test_demo_profile_lookup_and_enumeration():
    """Verify retrieval by ID, name, and enumeration."""
    profiles = get_all_demo_profiles()
    assert len(profiles) >= 2

    p_support = get_demo_profile("customer-support")
    assert p_support is not None
    assert p_support.profile_id == "customer-support"

    p_lead = get_demo_profile("lead-qualifier")
    assert p_lead is not None
    assert p_lead.profile_id == "lead-qualifier"

    # Fuzzy lookup by title
    p_by_name = get_demo_profile("Sales Lead Qualifier")
    assert p_by_name is not None
    assert p_by_name.profile_id == "lead-qualifier"


@pytest.mark.asyncio
async def test_demo_profile_api_endpoints_and_seeding(tmp_path):
    """Verify GET and POST seeding endpoints via ASGI client."""
    db_file = str(tmp_path / "test_demo_seed.db")
    await run_migrations(db_file)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. List profiles
        res_list = await client.get("/api/demo/profiles")
        assert res_list.status_code == 200
        profiles_data = res_list.json()
        assert len(profiles_data) >= 2
        ids = [p["profile_id"] for p in profiles_data]
        assert "customer-support" in ids
        assert "lead-qualifier" in ids

        # 2. Get specific profile
        res_get = await client.get("/api/demo/profiles/customer-support")
        assert res_get.status_code == 200
        assert res_get.json()["agent_name"] == "Customer Support Assistant"

        # 3. Seed profile
        res_seed = await client.post(
            "/api/demo/seed/customer-support",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        assert res_seed.status_code == 200
        seed_data = res_seed.json()
        assert seed_data["status"] == "seeded"
        assert seed_data["blueprint_id"] == "bp-customer-support"
        assert seed_data["tools_count"] >= 3
