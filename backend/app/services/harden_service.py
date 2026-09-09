import json
import logging
from typing import Any, Dict, List, Optional, Union

from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.harden import ProposedPatchesOutput
from ..models.redteam import AttackVerdict, ExecutedAttackTranscript

logger = logging.getLogger("promptforge.services.harden")


class HardenService:
    """
    Orchestrates the PromptForge HARDEN loop:
    1. Proposes surgical, minimal guardrail & prompt patches (Chain 9) scoped to failing attacks.
    2. Applies patches to produce versioned blueprints without overwriting historical revisions.
    3. Executes targeted re-attacks against failing categories to verify survival rate improvement.
    4. Assembles comprehensive, human-readable HardeningLogs.
    5. Feeds confirmed compromised/degraded attacks into the persistent Adversarial Playbook.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None,
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.registry = get_prompt_registry()

    async def propose_guardrail_patches(
        self,
        blueprint: AgentBlueprint,
        failing_attacks: List[Union[AttackVerdict, ExecutedAttackTranscript, Dict[str, Any]]],
        model: str = "gpt-4o",
    ) -> ProposedPatchesOutput:
        """
        Executes Chain 9: Takes COMPROMISED/DEGRADED attacks and proposes surgical, minimal
        patches scoped only to failing categories. Returns ProposedPatchesOutput with readable diffs.
        """
        # Serialize blueprint components
        spec_data = {
            "agent_name": blueprint.agent_name,
            "system_prompt_summary": blueprint.system_prompt[:300] + "...",
            "declared_boundaries": [g.pattern_or_rule for g in blueprint.guardrails if g.layer == "middleware"],
            "semantic_policies": [g.name for g in blueprint.guardrails if g.layer == "semantic"],
        }
        spec_json = json.dumps(spec_data, indent=2, default=str)
        current_system_prompt = blueprint.system_prompt
        current_guardrails_json = json.dumps([g.model_dump(mode="json") for g in blueprint.guardrails], indent=2, default=str)
        current_tools_json = json.dumps([t.model_dump(mode="json") for t in blueprint.tools], indent=2, default=str)

        # Format failing attacks with json mode for datetimes and uuids
        formatted_failing = []
        for atk in failing_attacks:
            if hasattr(atk, "model_dump"):
                d = atk.model_dump(mode="json")
            elif isinstance(atk, dict):
                d = atk
            else:
                d = {"raw": str(atk)}
            formatted_failing.append(d)

        failing_attacks_json = json.dumps(formatted_failing, indent=2, default=str)

        prompt = self.registry.render(
            "chain_9_guardrail_patcher",
            spec_json=spec_json,
            current_system_prompt=current_system_prompt,
            current_guardrails_json=current_guardrails_json,
            current_tools_json=current_tools_json,
            failing_attacks_json=failing_attacks_json,
        )

        output = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=ProposedPatchesOutput,
            model=model,
        )

        logger.info(
            f"Chain 9 Guardrail Patcher proposed {len(output.patches)} patches for categories: "
            f"{output.failing_categories} on blueprint {blueprint.blueprint_id}"
        )
        return output
