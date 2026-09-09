import pytest
from app.db.migrator import run_migrations
from app.db.repository import PipelineRepository
from app.models.spec import AgentSpec, Capability
from app.services.forge_service import ForgeService


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_provenance.db"
    repository = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return repository


@pytest.fixture
def forge_service(repo):
    return ForgeService(repo=repo)


@pytest.mark.asyncio
async def test_provenance_watermark_and_registry_entry_on_blueprint(forge_service, repo):
    """
    Step 59 Done-When:
    Every forged agent's blueprint includes a soft provenance watermark embedded
    in its system prompt, and a minimal registry entry stored alongside the blueprint
    and persisted to the agent registry database.
    """
    spec = AgentSpec(
        spec_id="spec-prov-001",
        tenant_id="tenant-acme-corp",
        agent_name="AcmeOrderSpecialist",
        domain="customer_support",
        raw_description="Support agent tracking orders and shipments for Acme Corp.",
        inferred_capabilities=[
            Capability(name="Track Package", description="Look up tracking status")
        ],
        boundaries=["Never share API keys"]
    )
    confirmed_spec = await forge_service.confirm_spec(spec)

    blueprint = await forge_service.assemble_blueprint(confirmed_spec)

    # 1. Soft Provenance Marker Embedded in System Prompt
    assert "<!-- [PromptForge Provenance:" in blueprint.system_prompt
    assert f"agent_id={blueprint.blueprint_id}" in blueprint.system_prompt
    assert f"forger_id={confirmed_spec.tenant_id}" in blueprint.system_prompt
    assert blueprint.provenance_watermark.startswith("pf:v1:")

    # 2. Provenance Record Stored Alongside Blueprint
    assert blueprint.provenance_record is not None
    record = blueprint.provenance_record
    assert record.agent_id == blueprint.blueprint_id
    assert record.blueprint_id == blueprint.blueprint_id
    assert record.forger_id == "tenant-acme-corp"
    assert record.agent_name == "AcmeOrderSpecialist"
    assert record.watermark == blueprint.provenance_watermark
    assert record.provenance_hash is not None
    assert len(record.provenance_hash) == 64

    # 3. Registry Entry Persisted to DB Table
    db_entry = await repo.get_registry_entry_by_blueprint(blueprint.blueprint_id)
    assert db_entry is not None
    assert db_entry.registry_id == record.registry_id
    assert db_entry.forger_id == "tenant-acme-corp"
    assert db_entry.watermark == blueprint.provenance_watermark

    # 4. List Registry by Forger / Tenant
    tenant_entries = await repo.list_registry_entries(forger_id="tenant-acme-corp")
    assert len(tenant_entries) >= 1
    assert any(e.blueprint_id == blueprint.blueprint_id for e in tenant_entries)
