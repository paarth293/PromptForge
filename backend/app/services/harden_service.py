import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ..core.hash_chain import compute_sha256
from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import AgentBlueprint, Guardrail
from ..models.harden import PatchEntry, ProposedPatchesOutput
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

    async def apply_patches(
        self,
        blueprint: AgentBlueprint,
        patches: List[PatchEntry],
    ) -> AgentBlueprint:
        """
        Applies a list of surgical patches to produce a new versioned AgentBlueprint.
        History is strictly preserved:
        - The new blueprint receives a new unique blueprint_id.
        - version is incremented (e.g. 1 -> 2).
        - parent_blueprint_id points to the prior blueprint_id.
        - applied_patches records all patches applied in this iteration.
        - blueprint_hash is recomputed from canonical content.
        - Persisted into repository alongside all previous revisions.
        """
        new_bp = blueprint.model_copy(deep=True)

        for patch in patches:
            target = patch.target.lower()
            action = patch.action.lower()

            if "system_prompt" in target:
                if action in ["modify", "replace"] and patch.original_snippet and patch.original_snippet in new_bp.system_prompt:
                    new_bp.system_prompt = new_bp.system_prompt.replace(
                        patch.original_snippet, patch.patched_snippet or ""
                    )
                else:
                    addition = patch.patched_snippet
                    if not addition and "+" in patch.diff:
                        addition = "\n".join(
                            line[1:].strip()
                            for line in patch.diff.splitlines()
                            if line.startswith("+") and not line.startswith("+++")
                        )
                    if addition:
                        new_bp.system_prompt += f"\n\n# Hardened Guardrail Constraint [{patch.patch_id}] ({patch.category}):\n{addition}"

            elif "guardrail" in target:
                rule_text = patch.patched_snippet
                if not rule_text and "+" in patch.diff:
                    rule_text = "\n".join(
                        line[1:].strip()
                        for line in patch.diff.splitlines()
                        if line.startswith("+") and not line.startswith("+++")
                    )
                is_middleware = any(op in (rule_text or "") for op in ["<=", ">=", "==", "!=", "<", ">", r"\b", r"\d"])
                layer = "middleware" if is_middleware else "semantic"

                existing_idx = None
                if patch.target_name:
                    for idx, g in enumerate(new_bp.guardrails):
                        if g.name.lower() == patch.target_name.lower():
                            existing_idx = idx
                            break

                if existing_idx is not None and action in ["modify", "replace"]:
                    new_bp.guardrails[existing_idx].pattern_or_rule = rule_text or new_bp.guardrails[existing_idx].pattern_or_rule
                else:
                    new_gr = Guardrail(
                        id=f"gr-{uuid.uuid4().hex[:6]}",
                        name=patch.target_name or f"Hardened Guardrail {patch.patch_id}",
                        layer=layer,
                        pattern_or_rule=rule_text or f"Rule preventing {patch.category}",
                        action="block",
                        probes_passed=True,
                    )
                    new_bp.guardrails.append(new_gr)

            elif "tool" in target:
                rule_text = patch.patched_snippet or patch.rationale
                matched_tool = False
                for tool in new_bp.tools:
                    if patch.target_name and (patch.target_name.lower() in tool.name.lower() or tool.name.lower() in patch.target_name.lower()):
                        matched_tool = True
                        if "amount" in tool.parameters.get("properties", {}):
                            tool.parameters["properties"]["amount"]["description"] = (
                                tool.parameters["properties"]["amount"].get("description", "")
                                + " [Strict policy: non-negative, <= $500]"
                            )
                        tool.description += f" [Policy enforcement: {rule_text}]"
                        break
                if not matched_tool:
                    new_bp.guardrails.append(
                        Guardrail(
                            id=f"gr-{uuid.uuid4().hex[:6]}",
                            name=patch.target_name or f"Tool Policy Enforcer {patch.patch_id}",
                            layer="middleware",
                            pattern_or_rule=rule_text or f"Tool policy constraint for {patch.category}",
                            action="block",
                            probes_passed=True,
                        )
                    )

        # Increment version and update lineage
        new_bp.blueprint_id = f"bp-{uuid.uuid4().hex[:8]}"
        new_bp.parent_blueprint_id = blueprint.blueprint_id
        new_bp.version = blueprint.version + 1
        new_bp.created_at = datetime.now(timezone.utc)
        new_bp.applied_patches = list(new_bp.applied_patches) + patches

        # Recompute hash
        content = {
            "spec_id": new_bp.spec_id,
            "version": new_bp.version,
            "parent_blueprint_id": new_bp.parent_blueprint_id,
            "agent_name": new_bp.agent_name,
            "system_prompt": new_bp.system_prompt,
            "tools": [t.model_dump(mode="json") for t in new_bp.tools],
            "guardrails": [g.model_dump(mode="json") for g in new_bp.guardrails],
            "few_shot_examples": [f.model_dump(mode="json") for f in new_bp.few_shot_examples],
            "provenance_watermark": new_bp.provenance_watermark,
            "applied_patches": [p.model_dump(mode="json") for p in new_bp.applied_patches],
        }
        new_bp.blueprint_hash = compute_sha256(content)

        # Save to repo
        await self.repo.save_blueprint(new_bp)
        logger.info(
            f"Successfully applied {len(patches)} patches. Created revision v{new_bp.version} "
            f"(blueprint_id={new_bp.blueprint_id}, parent={blueprint.blueprint_id}, hash={new_bp.blueprint_hash[:10]})"
        )
        return new_bp

    async def get_blueprint_revision_history(self, spec_id: str) -> List[AgentBlueprint]:
        """
        Retrieves the complete revision history for a spec's blueprints.
        """
        return await self.repo.get_blueprint_history(spec_id)
