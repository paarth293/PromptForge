"""Test that all warmup.py probes succeed against the FastAPI backend."""

import pytest
from app.db.migrator import run_migrations
from app.main import app
from httpx import ASGITransport, AsyncClient

from scripts.warmup import (
    probe_cost_report,
    probe_demo_profiles,
    probe_forge_pipeline,
    probe_hash_chain,
    probe_health,
    probe_runtime_chat,
)


@pytest.fixture(autouse=True)
async def init_test_db(tmp_path):
    db_file = str(tmp_path / "test_warmup_probes.db")
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
async def test_warmup_probes_all_green():
    """Confirms each probe in scripts/warmup.py passes cleanly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health probe
        health_ok = await probe_health(client)
        assert health_ok is True

        # 2. Demo profiles probe
        profiles = await probe_demo_profiles(client)
        assert profiles is not None
        assert "customer-support" in profiles
        assert "lead-qualifier" in profiles

        # 3. Forge pipeline seed probe
        bp_id = await probe_forge_pipeline(client, "customer-support")
        assert bp_id is not None
        assert bp_id == "bp-customer-support"

        # 4. Runtime chat probe
        chat_ok = await probe_runtime_chat(client, bp_id)
        assert chat_ok is True

        # 5. Cost report probe
        cost_ok = await probe_cost_report(client)
        assert cost_ok is True

        # 6. Hash chain probe
        chain_ok = await probe_hash_chain(client, bp_id)
        assert chain_ok is True
