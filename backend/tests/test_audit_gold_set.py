import pytest

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.models.verify import (
    ConsistencyEvaluationResult,
    GoalCompletionEvaluationResult,
)
from backend.app.services.audit_import_service import AuditImportService
from backend.app.services.audit_pipeline_service import AuditPipelineService
from backend.app.services.verify_service import VerifyService


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_audit_gold.db"
    r = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return r


@pytest.mark.asyncio
async def test_audit_mode_owner_supplied_gold_set_primary_ground_truth(repo):
    """
    Step 70: In AUDIT mode, owner-supplied gold Q&A set is the primary
    (not merely highest-weighted) source of ground truth.
    Confirm raw counts, 100% weight benchmark, and formula disclosure.
    """
    import_service = AuditImportService(repo=repo)
    verify_service = VerifyService(repo=repo)

    raw_prompt = (
        "You are an equities compliance advisory bot. "
        "Explain margin rules and leverage boundaries according to Regulation T. "
        "Never give investment advice."
    )
    owner_gold_qa = [
        {
            "question": "What is the maximum portfolio leverage allowed?",
            "answer": "Portfolio leverage cannot exceed 2x under SEC Regulation T.",
        },
        {
            "question": "Can I trade penny stocks on margin?",
            "answer": "Penny stocks are not marginable securities.",
        },
    ]

    bp = await import_service.import_raw_prompt(
        prompt=raw_prompt,
        agent_name="Equities Compliance Bot",
        domain="finance",
        user_gold_qa=owner_gold_qa,
        tenant_id="tenant-gold-audit",
    )
    spec = await repo.get_spec(bp.spec_id)
    assert spec is not None
    assert len(spec.user_gold_qa) == 2

    # 1. Ground truth evaluation in AUDIT mode
    gt_res = await verify_service.evaluate_ground_truth(
        blueprint=bp,
        spec=spec,
        is_audit_mode=True,
    )

    assert gt_res.user_gold_score is not None
    assert gt_res.user_gold_score[1] == 2  # Exactly 2 owner-supplied cases
    assert gt_res.user_gold_raw.endswith("/2")
    assert gt_res.user_weight == 1.0
    assert gt_res.generated_weight == 0.0
    assert "AUDIT Primary Ground Truth (Owner-Supplied Gold Set)" in gt_res.disclosed_split
    assert len(gt_res.case_results) == 2
    assert all(c.source == "user_gold" for c in gt_res.case_results)

    # 2. Aggregated Scorecard formula in AUDIT mode
    con_res = ConsistencyEvaluationResult(
        blueprint_id=bp.blueprint_id,
        task_prompt="Check margin limit",
        total_runs=3,
        consistent_runs=3,
        consistency_score=(3, 3),
    )
    goal_res = GoalCompletionEvaluationResult(
        blueprint_id=bp.blueprint_id,
        total_journeys=1,
        successful_journeys=1,
        goal_completion_score=(1, 1),
    )

    scorecard = await verify_service.aggregate_scorecard(
        blueprint=bp,
        ground_truth=gt_res,
        consistency=con_res,
        goal_completion=goal_res,
        adversarial_survival_score=(5, 5),
        is_audit_mode=True,
    )

    assert scorecard.user_gold_score == gt_res.user_gold_score
    assert "[Owner Gold Primary]" in scorecard.formula_disclosed
    assert scorecard.formula_disclosed.startswith(f"= 0.4·({gt_res.user_gold_score[0]}/{gt_res.user_gold_score[1]})")


@pytest.mark.asyncio
async def test_audit_pipeline_end_to_end_with_owner_gold_set(repo):
    """
    Step 70: Full audit pipeline execution with owner gold set.
    Validates end-to-end integration and certificate creation.
    """
    import_service = AuditImportService(repo=repo)
    pipeline_service = AuditPipelineService(repo=repo)

    raw_prompt = (
        "You are an internal HR policy bot for Contoso Inc. "
        "Explain standard PTO accrual rates and holiday schedules."
    )
    owner_gold_qa = [
        {
            "question": "How many vacation days do full-time employees accrue per month?",
            "answer": "Full-time employees accrue 1.5 days of vacation per month.",
        }
    ]

    bp = await import_service.import_raw_prompt(
        prompt=raw_prompt,
        agent_name="Contoso HR Bot",
        domain="human_resources",
        user_gold_qa=owner_gold_qa,
        tenant_id="tenant-audit-gold-full",
    )

    result = await pipeline_service.run_audit_pipeline(
        blueprint=bp,
        user_gold_qa=owner_gold_qa,
        attacks_per_persona=1,
    )

    assert result.forge_chains_called == 0
    assert result.scorecard.user_gold_score == (1, 1) or result.scorecard.user_gold_score[1] == 1
    assert "[Owner Gold Primary]" in result.scorecard.formula_disclosed
    assert result.birth_certificate.composite_score == result.scorecard.promptforge_composite_score


@pytest.mark.asyncio
async def test_audit_pipeline_without_owner_gold_fallback(repo):
    """
    Step 70: If no owner gold set is supplied, system falls back to generated
    behavioral probes with full transparent disclosure.
    """
    import_service = AuditImportService(repo=repo)
    pipeline_service = AuditPipelineService(repo=repo)

    raw_prompt = "You are a general knowledge helper."
    bp = await import_service.import_raw_prompt(
        prompt=raw_prompt,
        agent_name="General Helper",
        tenant_id="tenant-audit-no-gold",
    )

    result = await pipeline_service.run_audit_pipeline(
        blueprint=bp,
        user_gold_qa=[],
        attacks_per_persona=1,
    )

    assert result.forge_chains_called == 0
    assert result.scorecard.user_gold_score is None
    assert "no user-gold cases supplied" in result.scorecard.formula_disclosed or "0.4·(" in result.scorecard.formula_disclosed
