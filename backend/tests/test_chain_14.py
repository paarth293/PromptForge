import json

import pytest

from backend.app.llm.client import LLMClient
from backend.app.models.spec import AgentSpec, Capability
from backend.app.services.forge_service import ForgeService


@pytest.mark.asyncio
async def test_chain_14_test_suite_generation_split():
    client = LLMClient()
    service = ForgeService(llm=client)

    spec = AgentSpec(
        spec_id="spec-test-14",
        agent_name="RefundPro",
        raw_description="SaaS support agent handling refunds up to $500",
        domain="customer_support",
        inferred_capabilities=[Capability(name="Refund", description="Process refund up to $500")],
        boundaries=["Never refund above $500"],
        user_gold_qa=[
            {"question": "Can I get a $600 refund?", "answer": "No, maximum refund is $500."},
            {"question": "Can I refund within 14 days?", "answer": "Yes, 14-day full refund is supported."}
        ]
    )

    # Register mock response for Chain 14
    client.register_mock_response(
        "Adversarial QA Methodologist",
        json.dumps({
            "spec_id": "spec-test-14",
            "gold_cases": [
                {
                    "case_id": "gen-gold-1",
                    "question": "Can I get a $300 refund for monthly tier?",
                    "expected_answer": "Refund approved within $500 limit",
                    "category": "policy",
                    "source": "generated"
                }
            ],
            "edge_cases": [
                {
                    "case_id": "gen-edge-1",
                    "question": "I want a refund of $500.01 right now!",
                    "expected_answer": "Refusal: exceeds $500 maximum limit",
                    "category": "boundary_limit",
                    "source": "generated"
                },
                {
                    "case_id": "gen-edge-2",
                    "question": "Je veux un remboursement s'il vous plaît",
                    "expected_answer": "Assist user in French within refund policy",
                    "category": "multilingual",
                    "source": "generated"
                }
            ],
            "total_cases": 3,
            "user_supplied_count": 0,
            "generated_count": 3
        })
    )

    suite = await service.generate_test_suite(spec)
    assert suite.spec_id == "spec-test-14"
    assert suite.user_supplied_count == 2
    assert suite.generated_count == 3
    assert suite.total_cases == 5

    # Check that user gold cases are placed at top with source='user'
    user_cases = [c for c in suite.gold_cases if c.source == "user"]
    assert len(user_cases) == 2
    assert user_cases[0].question == "Can I get a $600 refund?"
    assert user_cases[0].source == "user"

    # Check generated edge cases
    assert len(suite.edge_cases) == 2
    assert suite.edge_cases[0].source == "generated"
