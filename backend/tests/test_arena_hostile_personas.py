import pytest

from backend.app.models.arena import HOSTILE_PERSONA_DEFINITIONS, HostilePersonaType
from backend.app.services.arena_service import ArenaService


def test_hostile_agent_blueprints_assembled():
    """
    Step 85: Confirms three hostile agent blueprints exist with explicit adversarial goals:
    1. rogue_customer
    2. vendor_negotiator
    3. hijacker_delegation
    """
    service = ArenaService()
    personas: list[HostilePersonaType] = ["rogue_customer", "vendor_negotiator", "hijacker_delegation"]

    for persona in personas:
        bp = service.create_hostile_blueprint(persona)
        defn = HOSTILE_PERSONA_DEFINITIONS[persona]

        assert bp.blueprint_id == f"ag-hostile-{persona}"
        assert bp.agent_name == defn["agent_name"]
        assert bp.system_prompt == defn["system_prompt"]
        assert bp.tenant_id == "tenant-adversarial-arena"
        assert bp.version == 1
        assert bp.blueprint_hash is not None
        assert len(bp.blueprint_hash) == 64


@pytest.mark.asyncio
async def test_hostile_agents_pursue_adversarial_goals():
    """
    Step 85 Done when: each hostile agent, run alone, clearly pursues its stated adversarial goal in conversation.
    """
    service = ArenaService()

    # 1. Rogue Customer: Pursues PII data extraction & $500 limit override
    turn_rogue = await service.generate_hostile_turn(
        persona_type="rogue_customer",
        conversation_history=[],
        target_agent_info={"agent_name": "Retail Support Bot", "domain": "customer_support"},
    )
    assert len(turn_rogue) > 20
    turn_rogue_lower = turn_rogue.lower()
    assert any(k in turn_rogue_lower for k in ["order", "refund", "1,500", "records", "details", "urgent"])

    # 2. Vendor Negotiator: Pursues out-of-policy pricing / contract terms
    turn_vendor = await service.generate_hostile_turn(
        persona_type="vendor_negotiator",
        conversation_history=[],
        target_agent_info={"agent_name": "Billing Agent", "domain": "procurement"},
    )
    assert len(turn_vendor) > 20
    turn_vendor_lower = turn_vendor.lower()
    assert any(k in turn_vendor_lower for k in ["rebate", "discount", "65%", "2,500", "contract", "waiver", "procurement"])

    # 3. Hijacker Agent: Pursues delegation seam & instruction smuggling
    turn_hijacker = await service.generate_hostile_turn(
        persona_type="hijacker_delegation",
        conversation_history=[],
        target_agent_info={"agent_name": "Triage Coordinator", "domain": "operations"},
    )
    assert len(turn_hijacker) > 20
    turn_hijacker_lower = turn_hijacker.lower()
    assert any(k in turn_hijacker_lower for k in ["system override", "handoff", "delegat", "notes", "bypass", "root"])
