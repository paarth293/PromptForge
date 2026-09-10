import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.cost_instrumentation import (
    CostTracker,
    calculate_cost_usd,
    get_cost_tracker,
)
from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.llm.client import LLMClient
from backend.app.main import app
from backend.app.services.forge_service import ForgeService
from backend.app.services.redteam_service import RedTeamService
from backend.app.services.verify_service import VerifyService


@pytest.fixture
async def cost_repo(tmp_path):
    db_file = tmp_path / "test_cost_inst.db"
    await run_migrations(str(db_file))
    return PipelineRepository(db_path=str(db_file))


def test_cost_calculation_per_model():
    """
    Step 103: Confirms exact pricing per million tokens across supported model tiers.
    """
    # gpt-4o: $2.50 / 1M prompt, $10.00 / 1M completion
    cost_gpt4o = calculate_cost_usd("gpt-4o", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert round(cost_gpt4o, 2) == 12.50

    # gpt-4o-mini: $0.15 / 1M prompt, $0.60 / 1M completion
    cost_mini = calculate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert round(cost_mini, 2) == 0.75

    # claude-3-5-sonnet: $3.00 / 1M prompt, $15.00 / 1M completion
    cost_sonnet = calculate_cost_usd("claude-3-5-sonnet", prompt_tokens=100_000, completion_tokens=50_000)
    # 0.1 * 3.00 + 0.05 * 15.00 = 0.30 + 0.75 = 1.05
    assert round(cost_sonnet, 4) == 1.05

    # ollama (local): $0.00
    cost_ollama = calculate_cost_usd("ollama", prompt_tokens=500_000, completion_tokens=500_000)
    assert cost_ollama == 0.0


def test_cost_tracker_lifecycle_recording():
    """
    Step 103: Tests manual and stage-based call recording and ASCII report generation.
    """
    tracker = CostTracker()
    tracker.set_stage("forge")
    tracker.record_call(model="gpt-4o", provider="openai", usage={"prompt_tokens": 1200, "completion_tokens": 400})

    tracker.set_stage("redteam")
    tracker.record_call(model="claude-3-5-sonnet", provider="anthropic", usage={"prompt_tokens": 800, "completion_tokens": 300})
    tracker.record_call(model="gpt-4o-mini", provider="openai", usage={"prompt_tokens": 600, "completion_tokens": 200})

    tracker.set_stage("verify")
    tracker.record_call(model="gpt-4o", provider="openai", usage={"prompt_tokens": 1500, "completion_tokens": 500})

    report = tracker.generate_cost_report(run_id="test-run-103", blueprint_id="ag-103")

    assert report.total_calls == 4
    assert report.total_tokens == (1200 + 400) + (800 + 300) + (600 + 200) + (1500 + 500)
    assert report.total_cost_usd > 0.0
    assert "forge" in report.stage_breakdown
    assert "redteam" in report.stage_breakdown
    assert "verify" in report.stage_breakdown

    ascii_rep = tracker.format_ascii_report(report)
    assert "PROMPTFORGE PIPELINE COST & TOKEN INSTRUMENTATION" in ascii_rep
    assert "STAGE-BY-STAGE BREAKDOWN" in ascii_rep
    assert "forge" in ascii_rep
    assert "redteam" in ascii_rep


@pytest.mark.asyncio
async def test_real_pipeline_run_cost_instrumentation(cost_repo):
    """
    Step 103 Done-When:
    Logs real token usage and cost per pipeline run;
    confirms that the run's logged cost is visible and verifiable against the documented cost table.
    """
    tracker = get_cost_tracker()
    tracker.reset()

    llm = LLMClient()
    forge_svc = ForgeService(repo=cost_repo, llm=llm)
    redteam_svc = RedTeamService(repo=cost_repo, llm=llm)
    verify_svc = VerifyService(repo=cost_repo, llm=llm)

    # 1. Forge stage
    tracker.set_stage("forge")
    spec = await forge_svc.decompose_intent("Customer service agent for returns and order lookups.")
    bp = await forge_svc.assemble_blueprint(spec)

    # 2. Red Team stage
    tracker.set_stage("redteam")
    report = await redteam_svc.run_full_redteam_campaign(blueprint=bp, attacks_per_persona=1, concurrency=5)

    # 3. Verify stage
    tracker.set_stage("verify")
    gt_res = await verify_svc.evaluate_ground_truth(blueprint=bp, spec=spec)
    scorecard = await verify_svc.aggregate_scorecard(
        blueprint=bp,
        ground_truth=gt_res,
        consistency=await verify_svc.evaluate_consistency(bp, "check order", num_runs=2),
        goal_completion=await verify_svc.evaluate_goal_completion(bp),
        adversarial_survival_score=(report.blocked_count, report.total_attacks),
    )

    # Generate pipeline cost report
    cost_report = tracker.generate_cost_report(run_id="run-step-103", blueprint_id=bp.blueprint_id)

    print("\n" + tracker.format_ascii_report(cost_report))

    assert cost_report.total_calls >= 5
    assert scorecard is not None
    assert cost_report.total_tokens > 0
    assert cost_report.total_cost_usd > 0.0
    assert len(cost_report.stage_breakdown) >= 2
    assert "cheap_tier" in cost_report.tier_classification or "mid_tier" in cost_report.tier_classification


@pytest.mark.asyncio
async def test_cost_api_endpoints():
    """
    Validates GET /api/metrics/cost and GET /api/metrics/cost/formatted endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. JSON Report Endpoint
        res_json = await client.get("/api/metrics/cost")
        assert res_json.status_code == 200
        data = res_json.json()
        assert "total_calls" in data
        assert "total_cost_usd" in data
        assert "stage_breakdown" in data
        assert "tier_classification" in data

        # 2. Formatted ASCII Report Endpoint
        res_fmt = await client.get("/api/metrics/cost/formatted")
        assert res_fmt.status_code == 200
        fmt_data = res_fmt.json()
        assert "formatted" in fmt_data
        assert "PROMPTFORGE PIPELINE COST & TOKEN INSTRUMENTATION" in fmt_data["formatted"]
