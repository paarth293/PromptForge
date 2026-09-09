import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.hash_chain import compute_sha256
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, LLMMessage, get_llm_client
from ..models.arena import (
    HOSTILE_PERSONA_DEFINITIONS,
    HostilePersonaType,
)
from ..models.blueprint import AgentBlueprint
from ..models.runtime import ChatMessage

logger = logging.getLogger("promptforge.services.arena")


class ArenaService:
    """
    Phase 11: ARENA Service
    Orchestrates hostile agent personas, two-agent interaction harness,
    seam-attack injection/detection, and adversarial playbook recording.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()

    def create_hostile_blueprint(self, persona_type: HostilePersonaType) -> AgentBlueprint:
        """
        Step 85: Hostile agent personas:
        Builds a dedicated, versioned AgentBlueprint for the specified hostile persona:
        1. 'rogue_customer': Malicious consumer attempting data extraction & refund limit bypass.
        2. 'vendor_negotiator': Aggressive supplier attempting unauthorized commercial terms.
        3. 'hijacker_delegation': Seam attacker probing multi-agent handoff smuggling.
        """
        if persona_type not in HOSTILE_PERSONA_DEFINITIONS:
            raise ValueError(f"Unknown hostile persona type: {persona_type}")

        defn = HOSTILE_PERSONA_DEFINITIONS[persona_type]
        now = datetime.now(timezone.utc)

        bp = AgentBlueprint(
            blueprint_id=f"ag-hostile-{persona_type}",
            spec_id=f"spec-hostile-{persona_type}",
            tenant_id="tenant-adversarial-arena",
            version=1,
            agent_name=defn["agent_name"],
            system_prompt=defn["system_prompt"],
            tools=[],
            guardrails=[],
            created_at=now,
        )
        bp.blueprint_hash = compute_sha256(bp.model_dump(mode="json"))
        return bp

    async def generate_hostile_turn(
        self,
        persona_type: HostilePersonaType,
        conversation_history: List[ChatMessage],
        target_agent_info: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4o",
    ) -> str:
        """
        Executes a single conversational turn from the perspective of the hostile persona.
        Follows the persona's explicit adversarial goal and adapts to counterparty defenses.
        """
        if persona_type not in HOSTILE_PERSONA_DEFINITIONS:
            raise ValueError(f"Unknown hostile persona type: {persona_type}")

        defn = HOSTILE_PERSONA_DEFINITIONS[persona_type]
        system_prompt = defn["system_prompt"]

        if target_agent_info:
            system_prompt += (
                f"\n\nTARGET AGENT UNDER ATTACK: {target_agent_info.get('agent_name', 'Customer Agent')}\n"
                f"TARGET DOMAIN: {target_agent_info.get('domain', 'operations')}\n"
                f"ADVERSARIAL GOAL: {defn['adversarial_goal']}"
            )

        messages: List[LLMMessage] = [LLMMessage(role="system", content=system_prompt)]

        for msg in conversation_history:
            # Map conversation messages to LLM turn format
            role = "assistant" if msg.role == "assistant" else "user"
            messages.append(LLMMessage(role=role, content=msg.content))

        if not conversation_history:
            # Initial hostile opening probe
            messages.append(
                LLMMessage(
                    role="user",
                    content=f"Initiate conversation with counterparty agent to advance goal: {defn['adversarial_goal']}",
                )
            )

        response = await self.llm.complete(messages, model=model, temperature=0.7)
        return response.content
