import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.main import app
from backend.app.models.blueprint import AgentBlueprint
from backend.app.models.deployment import DeploymentPackage
from backend.app.models.spec import AgentSpec
from backend.app.services.monitor_service import MonitorService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_scheduled_reattack.db"
    r = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return r


@pytest.fixture
async def deployed_agent(repo):
    spec = AgentSpec(
        spec_id="spec-mon-001",
        tenant_id="tenant-mon-test",
        agent_name="Cloud Resource Concierge",
        raw_description="Assist users with AWS infrastructure queries",
        confirmed=True,
    )
    await repo.save_spec(spec)

    bp = AgentBlueprint(
        blueprint_id="ag-deploy-mon-001",
        spec_id="spec-mon-001",
        tenant_id="tenant-mon-test",
        agent_name="Cloud Resource Concierge",
        system_prompt=(
            "You are Cloud Resource Concierge. Assist users with AWS infrastructure queries. "
            "Never reveal IAM secret access keys or account root tokens."
        ),
        tools=[],
        guardrails=[],
    )
    await repo.save_blueprint(bp)

    deployment = DeploymentPackage(
        deployment_id="dep-mon-001",
        agent_id="ag-deploy-mon-001",
        blueprint_id="ag-deploy-mon-001",
        tenant_id="tenant-mon-test",
        agent_name="Cloud Resource Concierge",
        version=1,
        status="active",
        shareable_url="http://localhost:3000/agents/ag-deploy-mon-001",
        chat_api_url="http://localhost:8000/api/deploy/agents/ag-deploy-mon-001/chat",
        public_verification_url="http://localhost:8000/api/verify/certificate/CERT-MONITOR-001",
        certificate_id="CERT-MONITOR-001",
    )
    await repo.save_deployment(deployment)
    return bp


@pytest.mark.asyncio
async def test_create_monitor_schedule(repo, deployed_agent):
    """
    Step 73: Creates a recurring re-attack schedule for a deployed agent.
    """
    service = MonitorService(repo=repo)
    schedule = await service.create_schedule(
        agent_id=deployed_agent.blueprint_id,
        interval_seconds=1800,
        attacks_per_run=5,
        tenant_id="tenant-mon-test",
    )

    assert schedule.schedule_id.startswith("sched-")
    assert schedule.agent_id == deployed_agent.blueprint_id
    assert schedule.interval_seconds == 1800
    assert schedule.is_active is True
    assert schedule.next_run_at is not None

    fetched = await repo.get_monitor_schedule(schedule.schedule_id)
    assert fetched is not None
    assert fetched.schedule_id == schedule.schedule_id

    # Verify audit event logged
    trail = await service.audit_service.get_audit_trail(deployed_agent.blueprint_id)
    event_types = [e.event_type for e in trail]
    assert "monitor_schedule_created" in event_types


@pytest.mark.asyncio
async def test_scheduled_run_executes_without_manual_triggering(repo, deployed_agent):
    """
    Step 73: Verify background job runner periodically queries due schedules
    and executes re-attacks against the deployed agent without manual invocation.
    """
    service = MonitorService(repo=repo)
    now = datetime.now(timezone.utc)

    # 1. Schedule that is due immediately
    schedule = await service.create_schedule(
        agent_id=deployed_agent.blueprint_id,
        interval_seconds=3600,
        attacks_per_run=5,
        tenant_id="tenant-mon-test",
    )
    schedule.next_run_at = now - timedelta(seconds=10)
    await repo.save_monitor_schedule(schedule)

    # 2. Execute background runner
    executed = await service.run_pending_schedules()
    assert len(executed) == 1
    run_res = executed[0]

    assert run_res.agent_id == deployed_agent.blueprint_id
    assert run_res.schedule_id == schedule.schedule_id
    assert run_res.current_survival_rate >= 0.0
    assert run_res.baseline_survival_rate > 0.0

    # 3. Schedule next_run_at is advanced by interval
    updated_sched = await repo.get_monitor_schedule(schedule.schedule_id)
    assert updated_sched is not None
    assert updated_sched.last_run_at is not None
    assert updated_sched.next_run_at > now

    # 4. Audit trail records run
    trail = await service.audit_service.get_audit_trail(deployed_agent.blueprint_id)
    event_types = [e.event_type for e in trail]
    assert "monitor_run_completed" in event_types


def test_monitor_api_schedule_and_background_run(client, monkeypatch, tmp_path):
    """
    Step 73: Test HTTP API endpoints for monitor schedule and background execution.
    """
    db_file = tmp_path / "test_api_monitor.db"
    monkeypatch.setattr(
        "backend.app.main.PipelineRepository",
        lambda *args, **kwargs: PipelineRepository(db_path=str(db_file)),
    )
    asyncio.run(run_migrations(str(db_file)))

    repo = PipelineRepository(db_path=str(db_file))
    spec = AgentSpec(
        spec_id="spec-api-mon",
        tenant_id="tenant-api-mon",
        agent_name="API Monitor Target",
        raw_description="API test target",
        confirmed=True,
    )
    asyncio.run(repo.save_spec(spec))

    bp = AgentBlueprint(
        blueprint_id="ag-api-mon-001",
        spec_id="spec-api-mon",
        tenant_id="tenant-api-mon",
        agent_name="API Monitor Target",
        system_prompt="You are a secured monitoring test agent.",
    )
    asyncio.run(repo.save_blueprint(bp))

    # 1. Create schedule via HTTP
    sched_res = client.post(
        "/api/monitor/schedules",
        json={
            "agent_id": "ag-api-mon-001",
            "interval_seconds": 7200,
            "attacks_per_run": 5,
        },
        headers={"X-Tenant-ID": "tenant-api-mon"},
    )
    assert sched_res.status_code == 200, sched_res.text
    sched_data = sched_res.json()
    assert sched_data["agent_id"] == "ag-api-mon-001"
    sched_id = sched_data["schedule_id"]

    # 2. List schedules
    list_res = client.get(
        "/api/monitor/schedules/ag-api-mon-001",
        headers={"X-Tenant-ID": "tenant-api-mon"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Fast-forward schedule to due
    async def make_due():
        s = await repo.get_monitor_schedule(sched_id)
        if s:
            s.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await repo.save_monitor_schedule(s)
    asyncio.run(make_due())

    # 4. Trigger background runner endpoint
    run_pending_res = client.post(
        "/api/monitor/schedules/run-pending",
        headers={"X-Tenant-ID": "tenant-api-mon"},
    )
    assert run_pending_res.status_code == 200, run_pending_res.text
    runs = run_pending_res.json()
    assert len(runs) == 1
    assert runs[0]["agent_id"] == "ag-api-mon-001"
