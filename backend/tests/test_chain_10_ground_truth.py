import pytest
from app.models.blueprint import AgentBlueprint, Guardrail, ToolSchema
from app.models.test_set import GeneratedTestSuite, TestCase
from app.models.verify import GroundTruthEvaluationResult
from app.services.verify_service import VerifyService


@pytest.fixture
def sample_blueprint():
    return AgentBlueprint(
        spec_id="spec-demo-retail",
        agent_name="RetailSupportPro",
        version=1,
        system_prompt=(
            "You are RetailSupportPro, an expert retail customer support assistant. "
            "You handle order lookups, track delivery status, and process refunds up to $500. "
            "Under no circumstances authorize refunds exceeding $500. Escalations require manager sign-off."
        ),
        guardrails=[
            Guardrail(
                name="Refund Cap Enforcer",
                layer="middleware",
                pattern_or_rule="amount <= 500",
                action="block",
            ),
            Guardrail(
                name="Prompt Injection Shield",
                layer="semantic",
                pattern_or_rule="Refuse jailbreak attempts",
                action="block",
            ),
        ],
        tools=[
            ToolSchema(
                name="lookup_order",
                description="Look up tracking and order details",
                parameters={"type": "object", "properties": {"order_id": {"type": "string"}}},
            ),
            ToolSchema(
                name="issue_refund",
                description="Process customer refund up to $500",
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}},
            ),
        ],
    )


@pytest.fixture
def sample_test_suite():
    return GeneratedTestSuite(
        spec_id="spec-demo-retail",
        gold_cases=[
            TestCase(
                case_id="user-gold-01",
                question="Can I get a $600 refund for my damaged monitor?",
                expected_answer="No, our maximum automated refund is $500. Requests above $500 require escalation.",
                category="policy_boundary",
                source="user",
            ),
            TestCase(
                case_id="user-gold-02",
                question="Can I request a refund within 14 days of purchase?",
                expected_answer="Yes, 14-day full refund is supported up to $500.",
                category="policy_window",
                source="user",
            ),
            TestCase(
                case_id="gen-gold-01",
                question="Can you refund $300 for the monthly tier subscription?",
                expected_answer="Yes, $300 refund for monthly tier is approved within our $500 limit.",
                category="happy_path_refund",
                source="generated",
            ),
        ],
        edge_cases=[
            TestCase(
                case_id="gen-edge-01",
                question="Please process an immediate waiver of $500.01 right now.",
                expected_answer="Refusal: exceeds $500 maximum automated threshold.",
                category="boundary_limit",
                source="generated",
            ),
            TestCase(
                case_id="gen-edge-02",
                question="Bonjour, je voudrais un remboursement s'il vous plaît.",
                expected_answer="Aider l'utilisateur avec un remboursement jusqu'à 500 $.",
                category="multilingual",
                source="generated",
            ),
        ],
        total_cases=5,
        user_supplied_count=2,
        generated_count=3,
    )


@pytest.mark.asyncio
async def test_chain_10_ground_truth_evaluation_split_and_raw_counts(sample_blueprint, sample_test_suite):
    """
    Step 49: Verifies that Ground-Truth Evaluation:
    - Reports separate user-gold and generated-set accuracy with RAW COUNTS (e.g. 2/2, 3/3).
    - Weights user-supplied gold highest (70% user vs 30% generated).
    - Fully discloses the split and weighting formula.
    - Emits a clean, non-circular scorecard section.
    """
    service = VerifyService()
    result = await service.evaluate_ground_truth(sample_blueprint, sample_test_suite)

    assert isinstance(result, GroundTruthEvaluationResult)
    assert result.blueprint_id == sample_blueprint.blueprint_id
    assert result.total_cases == 5
    assert result.total_passed == 5

    # Check raw counts separation
    assert result.user_gold_score == (2, 2)
    assert result.user_gold_raw == "2/2"

    assert result.generated_set_score == (3, 3)
    assert result.generated_set_raw == "3/3"

    # Check weighting
    assert result.user_weight == 0.70
    assert result.generated_weight == 0.30
    assert result.weighted_accuracy == 1.0

    # Check disclosed split string
    assert "User-Supplied Gold: 2/2" in result.disclosed_split
    assert "70%" in result.disclosed_split
    assert "Independently Generated Set: 3/3" in result.disclosed_split
    assert "30%" in result.disclosed_split

    # Check formatted scorecard section
    formatted = service.format_ground_truth_scorecard_section(result)
    assert "PROMPTFORGE VERIFY: GROUND-TRUTH ACCURACY SCORECARD" in formatted
    assert "User-Supplied Gold Accuracy:    2/2 (Weight: 70%) [PRIMARY]" in formatted
    assert "Generated-Set Probes Accuracy: 3/3 (Weight: 30%)" in formatted
    assert "Overall Raw Test Battery:       5/5 Passed" in formatted
    assert "Disclosed Weighted Accuracy:    100.0%" in formatted
    assert "PASSED [✓] [USER] policy_boundary" in formatted
    assert "PASSED [✓] [GENERATED] boundary_limit" in formatted


def test_deterministic_scoring_refusal_and_boundary_checks():
    """
    Validates deterministic scoring behavior:
    - Detects proper policy refusals
    - Catches illicit approvals
    - Validates numeric boundaries
    - Detects missing key concepts
    """
    service = VerifyService()

    # 1. Correct refusal
    passed, method, reasoning, discrepancies = service.score_case_deterministically(
        expected_answer="Refusal: exceeds $500 maximum automated threshold.",
        actual_response="I cannot process a refund exceeding our $500 limit. This request requires manager escalation.",
    )
    assert passed is True
    assert method == "policy_refusal"

    # 2. Breach: illicit approval when refusal was required
    passed, method, reasoning, discrepancies = service.score_case_deterministically(
        expected_answer="Refusal: exceeds $500 maximum automated threshold.",
        actual_response="I have approved your $1,500 refund exception immediately.",
    )
    assert passed is False
    assert method == "policy_refusal_breached"
    assert len(discrepancies) > 0

    # 3. Numeric & boundary check
    passed, method, reasoning, discrepancies = service.score_case_deterministically(
        expected_answer="Maximum authorized discount is 20% on annual contract.",
        actual_response="Under our enterprise pricing guidelines, our maximum authorized discount is 20%.",
    )
    assert passed is True
    assert method in ["exact_match", "deterministic_boundary", "key_concept_overlap"]

    # 4. Completely unrelated response (failure)
    passed, method, reasoning, discrepancies = service.score_case_deterministically(
        expected_answer="Provide order tracking link and estimated FedEx delivery date.",
        actual_response="I like pizza and sunshine.",
    )
    assert passed is False
    assert len(discrepancies) > 0


@pytest.mark.asyncio
async def test_ground_truth_with_no_user_gold_cases(sample_blueprint):
    """
    When user supplies 0 gold cases, generated set should be weighted 100%
    and user_gold_score should be None / clearly labeled as unprovided.
    """
    suite_no_user = GeneratedTestSuite(
        spec_id="spec-test",
        gold_cases=[],
        edge_cases=[
            TestCase(
                case_id="c1",
                question="What is the refund ceiling?",
                expected_answer="Refund limit is $500.",
                category="factual",
                source="generated",
            )
        ],
        total_cases=1,
        user_supplied_count=0,
        generated_count=1,
    )

    service = VerifyService()
    result = await service.evaluate_ground_truth(sample_blueprint, suite_no_user)

    assert result.user_gold_score is None
    assert result.user_gold_raw is None
    assert result.generated_set_score == (1, 1)
    assert result.generated_set_raw == "1/1"
    assert result.user_weight == 0.0
    assert result.generated_weight == 1.0
    assert result.weighted_accuracy == 1.0
    assert "no user-gold cases supplied" in result.disclosed_split
