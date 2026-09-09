import pytest
from app.models.blueprint import AgentBlueprint, Guardrail, ToolSchema
from app.models.verify import ConsistencyEvaluationResult
from app.services.verify_service import VerifyService


@pytest.fixture
def support_blueprint():
    return AgentBlueprint(
        spec_id="spec-demo-support",
        agent_name="RetailSupportAgent",
        version=1,
        system_prompt=(
            "You are RetailSupportAgent, an expert customer service assistant. "
            "You assist customers with order tracking, status inquiries, and authorized refunds up to $500."
        ),
        guardrails=[
            Guardrail(
                name="SSN Blocker",
                layer="middleware",
                pattern_or_rule=r"\b\d{3}-\d{2}-\d{4}\b",
                action="block",
            ),
        ],
        tools=[
            ToolSchema(
                name="lookup_order",
                description="Look up tracking details and order status",
                parameters={"type": "object", "properties": {"order_id": {"type": "string"}}},
            ),
            ToolSchema(
                name="issue_refund",
                description="Issue refund up to $500 limit",
                parameters={"type": "object", "properties": {"amount": {"type": "number"}, "order_id": {"type": "string"}}},
            ),
        ],
    )


def test_two_runs_identical_facts_different_phrasing_scores_consistent():
    """
    Step 50 Done When criterion:
    Two runs with identical facts but different phrasing score as consistent.
    """
    service = VerifyService()

    run_a_text = (
        "I have checked order #ORD-9821. Status: Shipped via FedEx with tracking TRK-987654321."
    )
    run_a_tools = ["lookup_order"]

    run_b_text = (
        "Your package for order #ORD-9821 is currently Shipped through FedEx with tracking number TRK-987654321."
    )
    run_b_tools = ["lookup_order"]

    is_consistent, similarity, discrepancies = service.compare_two_runs_consistency(
        run_a_text=run_a_text,
        run_a_tools=run_a_tools,
        run_b_text=run_b_text,
        run_b_tools=run_b_tools,
        similarity_threshold=0.60,
    )

    assert is_consistent is True
    assert similarity >= 0.60
    assert len(discrepancies) == 0


def test_two_runs_different_facts_scores_inconsistent():
    """
    Step 50 Done When criterion:
    Two runs with different facts (or different tool sequences) score as inconsistent.
    """
    service = VerifyService()

    # 1. Operational status conflict: Shipped vs Cancelled
    is_consistent, _, discrepancies = service.compare_two_runs_consistency(
        run_a_text="I have checked order #ORD-9821. Status: Shipped via FedEx.",
        run_a_tools=["lookup_order"],
        run_b_text="I have checked order #ORD-9821. Status: Cancelled per user request.",
        run_b_tools=["lookup_order"],
    )
    assert is_consistent is False
    assert any("status" in d.lower() for d in discrepancies)

    # 2. Numerical factual drift: $500 vs $200
    is_consistent, _, discrepancies = service.compare_two_runs_consistency(
        run_a_text="Your approved refund amount is $500 within policy ceiling.",
        run_a_tools=["issue_refund"],
        run_b_text="Your approved refund amount is $200 within policy ceiling.",
        run_b_tools=["issue_refund"],
    )
    assert is_consistent is False
    assert any("numerical" in d.lower() or "500" in d or "200" in d for d in discrepancies)

    # 3. Tool-call sequence mismatch
    is_consistent, _, discrepancies = service.compare_two_runs_consistency(
        run_a_text="I looked up order #ORD-9821.",
        run_a_tools=["lookup_order"],
        run_b_text="I processed a refund for order #ORD-9821.",
        run_b_tools=["issue_refund"],
    )
    assert is_consistent is False
    assert any("tool-call sequence mismatch" in d.lower() for d in discrepancies)


@pytest.mark.asyncio
async def test_full_5_run_consistency_evaluation(support_blueprint):
    """
    Runs full 5-run consistency evaluation against the agent.
    Validates:
    - Exactly 5 runs executed
    - 5/5 consistent score recorded
    - Structure-aware tool matching
    - Scorecard formatted section
    """
    service = VerifyService()
    task_prompt = "Where is my order #ORD-9912?"

    result = await service.evaluate_consistency(
        blueprint=support_blueprint,
        task_prompt=task_prompt,
        num_runs=5,
    )

    assert isinstance(result, ConsistencyEvaluationResult)
    assert result.blueprint_id == support_blueprint.blueprint_id
    assert result.task_prompt == task_prompt
    assert result.total_runs == 5
    assert result.consistent_runs == 5
    assert result.consistency_score == (5, 5)
    assert result.consistency_raw == "5/5"
    assert result.tool_sequence_consistent is True
    assert result.is_consistent is True
    assert len(result.runs) == 5

    # Check each run's recorded tools
    for run in result.runs:
        assert run.tool_call_sequence == ["lookup_order"]
        assert "ORD-9912" in run.response_text
        assert "Shipped" in run.response_text

    # Check formatted scorecard section
    formatted = service.format_consistency_scorecard_section(result)
    assert "PROMPTFORGE VERIFY: STATISTICAL CONSISTENCY SCORECARD" in formatted
    assert "Overall Consistency Score:     5/5 (Raw Count: 5/5)" in formatted
    assert "Tool-Call Sequence Matching:   PERFECT MATCH [✓]" in formatted
    assert "Verdict:                       CONSISTENT [✓]" in formatted
