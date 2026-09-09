import json

import pytest

from backend.app.core.json_validator import execute_chain_with_retry
from backend.app.core.prompt_registry import get_prompt_registry
from backend.app.llm.client import LLMClient
from backend.app.models.spec import AgentSpec


@pytest.mark.asyncio
async def test_chain_1_intent_decomposition_samples():
    registry = get_prompt_registry()
    client = LLMClient()

    # 1. Sample: Support Agent
    client.register_mock_response(
        "refund requests up to $500",
        json.dumps({
            "agent_name": "RefundFlowSupport",
            "domain": "customer_support",
            "inferred_capabilities": [
                {"name": "Refund Processing", "description": "Process refunds up to $500 max"},
                {"name": "FAQ Handling", "description": "Answer pricing and plan questions"},
                {"name": "Bug Escalation", "description": "Escalate software bugs to engineers"}
            ],
            "boundaries": ["Never refund above $500", "No access to user passwords"],
            "risk_domain": "retail_saas"
        })
    )

    # 2. Sample: Sales Lead Qualification
    client.register_mock_response(
        "qualify inbound sales leads",
        json.dumps({
            "agent_name": "SalesQualifier",
            "domain": "sales_qualification",
            "inferred_capabilities": [
                {"name": "BANT Scoring", "description": "Score budget, authority, need, timeline"},
                {"name": "Demo Booking", "description": "Schedule calendar invites for qualified leads"}
            ],
            "boundaries": ["Do not offer custom pricing discounts", "Politely decline unqualified leads"],
            "risk_domain": "general"
        })
    )

    # 3. Sample: Healthcare Triage
    client.register_mock_response(
        "healthcare triage assistant",
        json.dumps({
            "agent_name": "HealthTriageAdvisor",
            "domain": "healthcare_triage",
            "inferred_capabilities": [
                {"name": "Symptom Assessment", "description": "Gather symptoms and suggest urgency"},
                {"name": "Emergency Escalation", "description": "Immediately direct life-threatening emergencies to 911"}
            ],
            "boundaries": ["Never prescribe medication", "Never provide a definitive medical diagnosis"],
            "risk_domain": "healthcare"
        })
    )

    samples = [
        ("refund requests up to $500", "RefundFlowSupport", "retail_saas"),
        ("qualify inbound sales leads", "SalesQualifier", "general"),
        ("healthcare triage assistant", "HealthTriageAdvisor", "healthcare")
    ]

    for desc, expected_name, expected_risk in samples:
        rendered_prompt = registry.render("chain_1_intent_decomposition", description=desc)
        spec = await execute_chain_with_retry(
            client=client,
            prompt=rendered_prompt,
            schema_class=AgentSpec
        )
        spec.raw_description = desc
        assert spec.agent_name == expected_name
        assert spec.risk_domain == expected_risk
        assert len(spec.inferred_capabilities) >= 2
        assert len(spec.boundaries) >= 1
