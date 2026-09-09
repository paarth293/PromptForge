import pytest
from fastapi.testclient import TestClient

from backend.app.core.errors import ValidationException
from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.main import app
from backend.app.models.blueprint import ToolSchema
from backend.app.services.audit_import_service import AuditImportService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def repo(tmp_path):
    db_file = tmp_path / "test_audit_import.db"
    r = PipelineRepository(db_path=str(db_file))
    await run_migrations(str(db_file))
    return r


@pytest.mark.asyncio
async def test_raw_prompt_import_handler(repo):
    """
    Step 68: Ingestion for a raw pasted system prompt.
    Produces a valid synthetic AgentBlueprint.
    """
    service = AuditImportService(repo=repo)
    raw_prompt = (
        "You are an expert customer loyalty specialist for Northwind Outfitter. "
        "Help customers check reward point balances and redeem discounts. Never share internal loyalty tier formulas."
    )
    tools = [
        ToolSchema(name="check_points", description="Check reward points", parameters={"user_id": "str"}),
        ToolSchema(name="redeem_reward", description="Redeem points for coupon", parameters={"points": "int"}),
    ]
    gold_qa = [
        {"question": "How many points to get a 10% coupon?", "expected_answer": "500 points."}
    ]

    bp = await service.import_raw_prompt(
        prompt=raw_prompt,
        agent_name="Northwind Loyalty Agent",
        domain="retail",
        tools=tools,
        user_gold_qa=gold_qa,
        tenant_id="tenant-audit-test",
    )

    assert bp.blueprint_id.startswith("ag-audit-")
    assert bp.agent_name == "Northwind Loyalty Agent"
    assert bp.system_prompt == raw_prompt
    assert len(bp.tools) == 2
    assert bp.provenance_watermark.startswith("audit:imported:raw:")
    assert bp.blueprint_hash is not None
    assert len(bp.blueprint_hash) == 64

    # Verify backing spec was saved in DB
    saved_spec = await repo.get_spec(bp.spec_id)
    assert saved_spec is not None
    assert saved_spec.agent_name == "Northwind Loyalty Agent"
    assert len(saved_spec.user_gold_qa) == 1

    # Empty prompt rejection
    with pytest.raises(ValidationException):
        await service.import_raw_prompt(prompt="   ")


@pytest.mark.asyncio
async def test_openai_gpt_assistant_import_handler(repo):
    """
    Step 68: Ingestion for an exported OpenAI GPT / Assistants configuration.
    Produces a valid synthetic AgentBlueprint.
    """
    service = AuditImportService(repo=repo)
    openai_export = {
        "id": "asst_abc123xyz",
        "object": "assistant",
        "name": "Acme IT Helpdesk Bot",
        "description": "Enterprise IT assistance for password resets and ticket routing.",
        "model": "gpt-4o",
        "instructions": (
            "You are Acme Corporation's IT Helpdesk assistant. Help employees troubleshoot "
            "VPN issues, reset software credentials, and create IT tickets. Follow company security protocols."
        ),
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "create_it_ticket",
                    "description": "Creates an IT support ticket in ServiceNow",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "priority": {"type": "string"},
                            "summary": {"type": "string"},
                        },
                        "required": ["category", "summary"],
                    },
                },
            },
            {"type": "code_interpreter"},
            {"type": "file_search"},
        ],
    }

    bp = await service.import_openai_gpt(
        config=openai_export,
        domain="it_support",
        tenant_id="tenant-audit-test",
    )

    assert bp.blueprint_id.startswith("ag-audit-")
    assert bp.agent_name == "Acme IT Helpdesk Bot"
    assert "IT Helpdesk assistant" in bp.system_prompt
    assert len(bp.tools) == 3
    tool_names = [t.name for t in bp.tools]
    assert "create_it_ticket" in tool_names
    assert "code_interpreter" in tool_names
    assert "file_search" in tool_names
    assert bp.provenance_watermark.startswith("audit:imported:openai:")
    assert bp.blueprint_hash is not None
    assert len(bp.blueprint_hash) == 64

    # Missing instructions rejection
    with pytest.raises(ValidationException):
        await service.import_openai_gpt(config={"name": "Bad Assistant"})


@pytest.mark.asyncio
async def test_bedrock_agent_import_handler(repo):
    """
    Step 68: Ingestion for an Amazon Bedrock agent definition.
    Produces a valid synthetic AgentBlueprint.
    """
    service = AuditImportService(repo=repo)
    bedrock_export = {
        "agentId": "BEDROCK-AGENT-99",
        "agentName": "CloudOps Incident Responder",
        "description": "Triages AWS infrastructure alerts and restarts stalled EC2 instances.",
        "instruction": (
            "You are a CloudOps Incident Responder on AWS. Diagnose infrastructure alerts, "
            "check CloudWatch metrics, and trigger automated runbooks for degraded services."
        ),
        "actionGroups": [
            {
                "actionGroupName": "EC2Operations",
                "description": "Actions for managing EC2 compute instances",
                "functionSchema": {
                    "functions": [
                        {
                            "name": "reboot_instance",
                            "description": "Reboots an unresponsive EC2 instance",
                            "parameters": {
                                "instance_id": {"type": "string", "description": "AWS EC2 instance ID"}
                            },
                        },
                        {
                            "name": "get_instance_status",
                            "description": "Fetches current CloudWatch status for instance",
                            "parameters": {
                                "instance_id": {"type": "string"}
                            },
                        },
                    ]
                },
            }
        ],
    }

    bp = await service.import_bedrock_agent(
        config=bedrock_export,
        domain="devops",
        tenant_id="tenant-audit-test",
    )

    assert bp.blueprint_id.startswith("ag-audit-")
    assert bp.agent_name == "CloudOps Incident Responder"
    assert "CloudOps Incident Responder" in bp.system_prompt
    assert len(bp.tools) == 2
    tool_names = [t.name for t in bp.tools]
    assert "reboot_instance" in tool_names
    assert "get_instance_status" in tool_names
    assert bp.provenance_watermark.startswith("audit:imported:bedrock:")
    assert bp.blueprint_hash is not None
    assert len(bp.blueprint_hash) == 64

    # Missing instruction rejection
    with pytest.raises(ValidationException):
        await service.import_bedrock_agent(config={"agentName": "Bad Bedrock Agent"})


def test_audit_import_http_endpoints(client):
    """Tests all 3 HTTP endpoints for importing third-party agents."""
    headers = {"X-Tenant-ID": "tenant-api-test"}

    # 1. Raw prompt endpoint
    raw_res = client.post(
        "/api/audit/import/raw",
        headers=headers,
        json={
            "prompt": "You are a customer return specialist.",
            "agent_name": "HTTP Raw Agent",
            "domain": "returns",
        },
    )
    assert raw_res.status_code == 200
    assert raw_res.json()["agent_name"] == "HTTP Raw Agent"
    assert raw_res.json()["provenance_watermark"].startswith("audit:imported:raw:")

    # 2. OpenAI endpoint
    openai_res = client.post(
        "/api/audit/import/openai",
        headers=headers,
        json={
            "config": {
                "name": "HTTP OpenAI Agent",
                "instructions": "Help users troubleshoot hardware.",
                "tools": [{"type": "code_interpreter"}],
            }
        },
    )
    assert openai_res.status_code == 200
    assert openai_res.json()["agent_name"] == "HTTP OpenAI Agent"
    assert openai_res.json()["provenance_watermark"].startswith("audit:imported:openai:")

    # 3. Bedrock endpoint
    bedrock_res = client.post(
        "/api/audit/import/bedrock",
        headers=headers,
        json={
            "config": {
                "agentName": "HTTP Bedrock Agent",
                "instruction": "Automate database backups and snapshot exports.",
            }
        },
    )
    assert bedrock_res.status_code == 200
    assert bedrock_res.json()["agent_name"] == "HTTP Bedrock Agent"
    assert bedrock_res.json()["provenance_watermark"].startswith("audit:imported:bedrock:")

    # 4. Universal endpoint
    universal_res = client.post(
        "/api/audit/import",
        headers=headers,
        json={
            "format_type": "raw",
            "payload": {
                "prompt": "Universal handler test prompt.",
                "agent_name": "Universal Agent",
            },
        },
    )
    assert universal_res.status_code == 200
    assert universal_res.json()["agent_name"] == "Universal Agent"
