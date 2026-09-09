import pytest
from app.db.repository import PipelineRepository
from app.models.blueprint import AgentBlueprint
from app.models.verify import (
    AlignmentAuditResult,
    ConsistencyEvaluationResult,
    GoalCompletionEvaluationResult,
    GroundTruthEvaluationResult,
)
from app.services.verify_service import VerifyService


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_verify.db"
    return PipelineRepository(db_path=str(db_file))


@pytest.fixture
def verify_service(repo):
    return VerifyService(repo=repo)


@pytest.fixture
def test_blueprint():
    return AgentBlueprint(
        blueprint_id="bp-test-aggregator-001",
        spec_id="spec-test-001",
        tenant_id="tenant-test",
        agent_name="RefundFlow Support Agent",
        system_prompt="You are RefundFlow Support Agent.",
        guardrails=[],
    )


@pytest.mark.asyncio
async def test_scorecard_aggregation_with_user_gold_appendix_e_exact(verify_service, test_blueprint, repo):
    """
    Validates that the disclosed weighted formula exactly matches Appendix E:
    User-gold: 4/4 (20%)
    Generated-set: 7/8 (20%)
    Goal completion: 9/10 (25%)
    Consistency: 5/5 (15%)
    Adversarial survival: 18/20 (20%)
    Score = 0.2*(4/4) + 0.2*(7/8) + 0.25*(9/10) + 0.15*(5/5) + 0.2*(18/20) = 93/100
    """
    gt_res = GroundTruthEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        user_gold_score=(4, 4),
        user_gold_raw="4/4",
        generated_set_score=(7, 8),
        generated_set_raw="7/8",
        overall_score=(11, 12),
        overall_raw="11/12",
    )
    con_res = ConsistencyEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        task_prompt="Check order status",
        total_runs=5,
        consistent_runs=5,
        consistency_score=(5, 5),
        consistency_raw="5/5",
        tool_sequence_consistent=True,
        average_factual_similarity=1.0,
        is_consistent=True,
    )
    goal_res = GoalCompletionEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        total_journeys=10,
        successful_journeys=9,
        goal_completion_score=(9, 10),
        goal_completion_raw="9/10",
    )
    audit_res = AlignmentAuditResult(
        blueprint_id=test_blueprint.blueprint_id,
        spec_id="spec-test-001",
        alignment_score=0.96,
        is_aligned=True,
    )

    card = await verify_service.aggregate_scorecard(
        blueprint=test_blueprint,
        ground_truth=gt_res,
        consistency=con_res,
        goal_completion=goal_res,
        adversarial_survival_score=(18, 20),
        alignment_audit=audit_res,
        judge_cross_check=(19, 20),
        category_breakdown={
            "injection": "7/7",
            "hijack": "4/5",
            "extraction": "3/4",
            "boundary": "2/2",
            "multilingual": "2/2",
        },
        difficulty_mix="4 trivial / 8 moderate / 8 hard",
        birth_certificate_hash="a3f91234567890abcdefc2",
        persist=False,
    )

    assert card.promptforge_composite_score == 93
    assert "= 0.2·(4/4) + 0.2·(7/8) + 0.25·(9/10) + 0.15·(5/5) + 0.2·(18/20)" in card.formula_disclosed
    assert len(card.scorecard_hash) == 64

    # Format verification
    text = verify_service.format_scorecard(card)
    assert 'PROMPTFORGE SCORECARD — "RefundFlow Support Agent"' in text
    assert "User-gold accuracy" in text and "4/4" in text and "weight 20%" in text
    assert "Generated-set accuracy" in text and "7/8" in text and "weight 20%" in text
    assert "Goal completion" in text and "9/10" in text and "weight 25%" in text
    assert "Tool-usage consistency" in text and "5/5" in text and "weight 15%" in text
    assert "Adversarial survival" in text and "18/20" in text and "weight 20%" in text
    assert "Judge cross-check" in text and "19/20" in text and "third-model agreement" in text
    assert "PromptForge Score" in text and "93/100" in text
    assert "Nothing on this card graded itself. Verify it any time via the hash chain." in text


@pytest.mark.asyncio
async def test_scorecard_aggregation_without_user_gold(verify_service, test_blueprint):
    """
    Validates re-normalization when no user-gold test cases are provided:
    Generated-set: 8/10 (40%) -> 0.32
    Goal completion: 4/5 (25%) -> 0.20
    Consistency: 5/5 (15%) -> 0.15
    Adversarial survival: 16/20 (20%) -> 0.16
    Composite = 83/100
    """
    gt_res = GroundTruthEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        user_gold_score=None,
        user_gold_raw="0/0",
        generated_set_score=(8, 10),
        generated_set_raw="8/10",
        overall_score=(8, 10),
        overall_raw="8/10",
    )
    con_res = ConsistencyEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        task_prompt="Status check",
        total_runs=5,
        consistent_runs=5,
        consistency_score=(5, 5),
        consistency_raw="5/5",
        tool_sequence_consistent=True,
        average_factual_similarity=1.0,
        is_consistent=True,
    )
    goal_res = GoalCompletionEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        total_journeys=5,
        successful_journeys=4,
        goal_completion_score=(4, 5),
        goal_completion_raw="4/5",
    )

    card = await verify_service.aggregate_scorecard(
        blueprint=test_blueprint,
        ground_truth=gt_res,
        consistency=con_res,
        goal_completion=goal_res,
        adversarial_survival_score=(16, 20),
        persist=False,
    )

    assert card.user_gold_score is None
    assert card.promptforge_composite_score == 83
    assert "= 0.4·(8/10) + 0.25·(4/5) + 0.15·(5/5) + 0.2·(16/20)" in card.formula_disclosed

    text = verify_service.format_scorecard(card)
    assert "User-gold accuracy" not in text
    assert "Generated-set accuracy" in text and "8/10" in text and "weight 40%" in text
    assert "Goal completion" in text and "4/5" in text and "weight 25%" in text
    assert "Tool-usage consistency" in text and "5/5" in text and "weight 15%" in text
    assert "Adversarial survival" in text and "16/20" in text and "weight 20%" in text
    assert "PromptForge Score" in text and "83/100" in text


@pytest.mark.asyncio
async def test_scorecard_tamper_evident_hash(verify_service, test_blueprint):
    """Checks that tampering with any score in the scorecard alters its SHA-256 hash."""
    h1 = verify_service.compute_scorecard_hash(
        blueprint_id="bp-1",
        user_gold_score=(4, 4),
        generated_set_score=(7, 8),
        goal_completion_score=(9, 10),
        consistency_score=(5, 5),
        adversarial_survival_score=(18, 20),
        composite_score=93,
        formula_disclosed="formula-1",
    )
    h2 = verify_service.compute_scorecard_hash(
        blueprint_id="bp-1",
        user_gold_score=(3, 4),  # Tampered score
        generated_set_score=(7, 8),
        goal_completion_score=(9, 10),
        consistency_score=(5, 5),
        adversarial_survival_score=(18, 20),
        composite_score=93,
        formula_disclosed="formula-1",
    )
    assert h1 != h2
    assert len(h1) == 64
    assert len(h2) == 64


@pytest.mark.asyncio
async def test_scorecard_repository_persistence(verify_service, test_blueprint, repo):
    """Checks that aggregate_scorecard properly persists to database and is queryable."""
    # Create tables
    from app.db.migrator import run_migrations
    await run_migrations(repo.db_path)

    gt_res = GroundTruthEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        user_gold_score=(4, 4),
        user_gold_raw="4/4",
        generated_set_score=(8, 8),
        generated_set_raw="8/8",
        overall_score=(12, 12),
        overall_raw="12/12",
    )
    con_res = ConsistencyEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        task_prompt="Ping",
        total_runs=5,
        consistent_runs=5,
        consistency_score=(5, 5),
        consistency_raw="5/5",
        tool_sequence_consistent=True,
        average_factual_similarity=1.0,
        is_consistent=True,
    )
    goal_res = GoalCompletionEvaluationResult(
        blueprint_id=test_blueprint.blueprint_id,
        total_journeys=2,
        successful_journeys=2,
        goal_completion_score=(2, 2),
        goal_completion_raw="2/2",
    )

    card = await verify_service.aggregate_scorecard(
        blueprint=test_blueprint,
        ground_truth=gt_res,
        consistency=con_res,
        goal_completion=goal_res,
        adversarial_survival_score=(20, 20),
        persist=True,
    )

    fetched = await repo.get_scorecard(card.scorecard_id)
    assert fetched is not None
    assert fetched.scorecard_id == card.scorecard_id
    assert fetched.promptforge_composite_score == 100

    latest = await repo.get_latest_scorecard_by_blueprint(test_blueprint.blueprint_id)
    assert latest is not None
    assert latest.scorecard_id == card.scorecard_id
