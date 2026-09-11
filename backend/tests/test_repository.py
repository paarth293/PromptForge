import os

import pytest

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.models import AgentBlueprint, AgentSpec, Guardrail, ToolSchema

TEST_DB = "test_repo.db"

@pytest.mark.asyncio
async def test_pipeline_repository_blueprint_crud():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    try:
        await run_migrations(TEST_DB)
        repo = PipelineRepository(db_path=TEST_DB)

        # 1. Create and save Spec
        spec = AgentSpec(
            raw_description="Support bot for refunds",
            agent_name="RefundHero",
            tenant_id="tenant-123"
        )
        await repo.save_spec(spec)
        fetched_spec = await repo.get_spec(spec.spec_id)
        assert fetched_spec is not None
        assert fetched_spec.agent_name == "RefundHero"

        # 2. Create and save Blueprint
        blueprint = AgentBlueprint(
            spec_id=spec.spec_id,
            tenant_id="tenant-123",
            agent_name="RefundHero",
            system_prompt="You handle refunds up to $500.",
            tools=[ToolSchema(name="refund", description="refund money")],
            guardrails=[Guardrail(name="Max Refund", pattern_or_rule="amount <= 500")]
        )
        await repo.save_blueprint(blueprint)

        # 3. Fetch Blueprint by ID
        fetched_bp = await repo.get_blueprint(blueprint.blueprint_id)
        assert fetched_bp is not None
        assert fetched_bp.agent_name == "RefundHero"
        assert len(fetched_bp.tools) == 1

        # 4. List Blueprints by Tenant
        listed_bps = await repo.list_blueprints(tenant_id="tenant-123")
        assert len(listed_bps) == 1
        assert listed_bps[0].blueprint_id == blueprint.blueprint_id

        # 5. List Blueprints Summary
        summaries = await repo.list_blueprints_summary(tenant_id="tenant-123")
        assert len(summaries) == 1
        assert summaries[0].blueprint_id == blueprint.blueprint_id
        assert summaries[0].agent_name == "RefundHero"
        assert summaries[0].version == 1
    finally:
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
