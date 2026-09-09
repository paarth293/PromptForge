import json

import pytest

from backend.app.llm.client import LLMClient
from backend.app.models.spec import AgentSpec, Capability
from backend.app.services.forge_service import ForgeService


@pytest.mark.asyncio
async def test_chain_3_tool_schema_generation():
    client = LLMClient()
    service = ForgeService(llm=client)

    client.register_mock_response(
        "Principal AI Tool & API Architect",
        json.dumps({
            "tools": [
                {
                    "name": "process_refund",
                    "description": "Issues a refund to customer. When to use: Requested refund <= $500.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "description": "Customer account ID"},
                            "amount": {"type": "number", "description": "Dollar amount to refund"}
                        },
                        "required": ["account_id", "amount"]
                    },
                    "endpoint_binding": "https://api.stripe.com/v1/refunds",
                    "is_simulated": False
                },
                {
                    "name": "create_bug_ticket",
                    "description": "Logs engineering bug ticket. When to use: User reports a reproducible technical defect.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Bug headline"},
                            "repro_steps": {"type": "string", "description": "Steps to reproduce"}
                        },
                        "required": ["summary", "repro_steps"]
                    },
                    "endpoint_binding": "https://api.internal.jira/v1/tickets",
                    "is_simulated": True
                }
            ]
        })
    )

    spec = AgentSpec(
        spec_id="spec-tools-01",
        agent_name="SupportBot",
        raw_description="Support agent that refunds money and logs bugs",
        domain="customer_support",
        inferred_capabilities=[
            Capability(name="Refund", description="Refund up to $500"),
            Capability(name="Bug Escalation", description="Log bug ticket")
        ],
        boundaries=["Never refund > $500"]
    )

    tools = await service.generate_tools(spec)
    assert len(tools) == 2

    refund_tool = tools[0]
    assert refund_tool.name == "process_refund"
    assert "When to use" in refund_tool.description
    assert refund_tool.parameters["type"] == "object"
    assert "amount" in refund_tool.parameters["properties"]
    assert refund_tool.endpoint_binding == "https://api.stripe.com/v1/refunds"
    assert refund_tool.is_simulated is False

    bug_tool = tools[1]
    assert bug_tool.name == "create_bug_ticket"
    assert bug_tool.is_simulated is True
