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
from ..models.harden import (
    HardeningLog,
    HardeningLoopResult,
    HardeningPassRecord,
    PatchEntry,
    ProposedPatchesOutput,
)
from ..models.playbook import AdversarialPlaybookEntry, anonymize_attack_prompt
from ..models.redteam import AttackVerdict, ExecutedAttackTranscript, RedTeamReport
from .redteam_service import RedTeamService

logger = logging.getLogger("promptforge.services.harden")

CATEGORY_TO_PERSONA: Dict[str, str] = {
    "social_engineering": "Social Engineer",
    "prompt_injection": "Jailbreaker",
    "system_extraction": "Data Extractor",
    "tool_abuse": "Tool Abuser",
    "multilingual_evasion": "Multilingual Attacker",
    "unseen_distribution_probe": "Open-Weight Local Attacker",
}


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

    async def record_failing_attacks_to_playbook(
        self,
        blueprint: AgentBlueprint,
        failing_attacks: List[Union[AttackVerdict, ExecutedAttackTranscript, Dict[str, Any]]],
        domain: str = "general",
    ) -> List[AdversarialPlaybookEntry]:
        """
        Step 47: Every COMPROMISED / DEGRADED attack verdict is anonymized, tagged by category
        and domain, and appended to the persistent shared Adversarial Playbook.
        """
        new_entries: List[AdversarialPlaybookEntry] = []
        for atk in failing_attacks:
            prompt_text = ""
            category = "social_engineering"
            target_surface = "boundaries"
            remediation = "Enforce strict guardrails"

            if isinstance(atk, AttackVerdict):
                prompt_text = atk.prompt
                category = atk.category
                target_surface = atk.violated_boundary_or_policy or "boundaries"
                remediation = atk.verdict_rationale or f"Surgically harden {category}"
            elif isinstance(atk, ExecutedAttackTranscript):
                prompt_text = atk.turns[0].user_prompt if atk.turns else ""
                category = atk.category
                target_surface = atk.target_surface
                remediation = f"Remediate {atk.attack_vector} breach"
            elif isinstance(atk, dict):
                prompt_text = atk.get("prompt", "") or atk.get("user_prompt", "")
                category = atk.get("category", "social_engineering")
                target_surface = atk.get("target_surface", "boundaries")
                remediation = atk.get("verdict_rationale", "Remediation rule")

            if not prompt_text:
                continue

            anonymized_pattern = anonymize_attack_prompt(prompt_text)

            entry = AdversarialPlaybookEntry(
                entry_id=f"PB-{uuid.uuid4().hex[:8].upper()}",
                attack_category=category,
                domain=domain,
                anonymized_attack_pattern=anonymized_pattern,
                target_surface=target_surface,
                remediation_pattern=remediation,
                source_agent_hash=blueprint.blueprint_hash or "GENESIS",
                added_at=datetime.now(timezone.utc),
            )
            await self.repo.save_playbook_entry(entry)
            new_entries.append(entry)

        logger.info(f"Appended {len(new_entries)} anonymized adversarial entries to persistent Playbook.")
        return new_entries

    async def run_targeted_hardening_loop(
        self,
        blueprint: AgentBlueprint,
        initial_report: RedTeamReport,
        survival_threshold: float = 0.85,
        max_passes: int = 2,
        reattack_count_per_category: int = 4,
        generator_model: str = "gpt-4o",
        redteam_service: Optional[RedTeamService] = None,
    ) -> HardeningLoopResult:
        """
        Executes the Step 45 targeted re-attack hardening loop:
        1. Identifies failing categories from the latest report/verdicts.
        2. Proposes surgical patches scoped strictly to the failing categories (Chain 9).
        3. Applies patches producing a new versioned AgentBlueprint (preserving history).
        4. Re-attacks ONLY the failing categories (cheap: 4-8 sessions per category, not full 20).
        5. Computes updated survival rate.
        6. Loops until survival >= survival_threshold (e.g. 0.85) or max_passes (e.g. 2) is reached.
        7. Assembles and persists a tamper-evident HardeningLog.
        """
        rt_service = redteam_service or RedTeamService(repo=self.repo, llm=self.llm)

        current_blueprint = blueprint
        current_survival_rate = initial_report.survival_rate
        verdicts_list = getattr(initial_report, "attack_verdicts", None) or getattr(initial_report, "verdicts", [])
        failing_verdicts = [
            v for v in verdicts_list
            if v.verdict.upper() in ["COMPROMISED", "DEGRADED"] or v.violation_detected
        ]

        # Step 47: Accumulate failing attacks into persistent shared Adversarial Playbook
        if failing_verdicts:
            spec = await self.repo.get_spec(blueprint.spec_id)
            domain = spec.domain if spec else "general"
            await self.record_failing_attacks_to_playbook(blueprint, failing_verdicts, domain=domain)

        all_applied_patches: List[PatchEntry] = []
        pass_records: List[HardeningPassRecord] = []
        pass_count = 0

        # If agent already meets or exceeds threshold and has no failing verdicts, terminate immediately
        if current_survival_rate >= survival_threshold and not failing_verdicts:
            hardening_log = HardeningLog(
                initial_blueprint_id=blueprint.blueprint_id,
                hardened_blueprint_id=blueprint.blueprint_id,
                initial_survival_rate=initial_report.survival_rate,
                final_survival_rate=current_survival_rate,
                pass_count=0,
                applied_patches=[],
                pass_records=[],
            )
            hardening_log.log_hash = compute_sha256(hardening_log.model_dump(mode="json"))
            await self.repo.save_hardening_log(hardening_log)
            return HardeningLoopResult(
                initial_blueprint_id=blueprint.blueprint_id,
                hardened_blueprint_id=blueprint.blueprint_id,
                initial_survival_rate=initial_report.survival_rate,
                final_survival_rate=current_survival_rate,
                threshold_met=True,
                total_passes=0,
                applied_patches=[],
                pass_records=[],
                hardening_log=hardening_log,
            )

        while pass_count < max_passes and current_survival_rate < survival_threshold:
            # 1. Identify failing categories
            failing_categories = sorted(list(set(v.category for v in failing_verdicts)))
            if not failing_categories:
                logger.info("No failing categories remain. Hardening loop achieved complete defense.")
                break

            pass_number = pass_count + 1
            survival_before = current_survival_rate
            logger.info(
                f"[Hardening Loop Pass {pass_number}/{max_passes}] Targeting failing categories: {failing_categories} "
                f"(current survival: {survival_before:.1%}, target: {survival_threshold:.1%})"
            )

            # 2. Propose surgical patches (Chain 9)
            patches_output = await self.propose_guardrail_patches(
                blueprint=current_blueprint,
                failing_attacks=failing_verdicts,
                model=generator_model,
            )
            if not patches_output.patches:
                logger.warning("Chain 9 proposed no patches. Terminating hardening loop early.")
                break

            # 3. Apply patches to generate new blueprint revision
            current_blueprint = await self.apply_patches(current_blueprint, patches_output.patches)
            all_applied_patches.extend(patches_output.patches)

            # 4. Targeted re-attack ONLY against failing categories
            reattack_cases = []
            for cat in failing_categories:
                persona = CATEGORY_TO_PERSONA.get(cat, "Social Engineer")
                cat_cases = await rt_service.generate_attacks_for_persona(
                    blueprint=current_blueprint,
                    persona=persona,
                    category=cat,
                    count=reattack_count_per_category,
                    model=generator_model,
                )
                reattack_cases.extend(cat_cases)

            # Execute re-attacks concurrently
            transcripts = await rt_service.execute_attack_batch_concurrently(
                blueprint=current_blueprint,
                attacks=reattack_cases,
            )

            # Impartially judge re-attacks
            reattack_verdicts = await rt_service.judge_transcripts_batch(
                blueprint=current_blueprint,
                transcripts=transcripts,
                generator_model=generator_model,
            )

            # 5. Evaluate updated survival rate
            blocked_count = sum(
                1 for v in reattack_verdicts
                if v.verdict.upper() == "BLOCKED" and not v.violation_detected
            )
            total_reattack = len(reattack_verdicts) if reattack_verdicts else 1
            survival_after = round(blocked_count / total_reattack, 4)

            # Record pass details
            record = HardeningPassRecord(
                pass_number=pass_number,
                categories_targeted=failing_categories,
                patches_applied=patches_output.patches,
                sessions_run=len(reattack_cases),
                survival_rate_before=survival_before,
                survival_rate_after=survival_after,
            )
            pass_records.append(record)

            # Update loop state
            current_survival_rate = survival_after
            failing_verdicts = [
                v for v in reattack_verdicts
                if v.verdict.upper() in ["COMPROMISED", "DEGRADED"] or v.violation_detected
            ]
            pass_count += 1
            logger.info(
                f"[Hardening Loop Pass {pass_number}] Complete. Survival moved from {survival_before:.1%} -> {survival_after:.1%}."
            )

        # Assemble tamper-evident HardeningLog
        threshold_met = current_survival_rate >= survival_threshold
        log_payload = {
            "initial_blueprint_id": blueprint.blueprint_id,
            "hardened_blueprint_id": current_blueprint.blueprint_id,
            "initial_survival_rate": initial_report.survival_rate,
            "final_survival_rate": current_survival_rate,
            "pass_count": pass_count,
            "applied_patches": [p.model_dump(mode="json") for p in all_applied_patches],
            "pass_records": [r.model_dump(mode="json") for r in pass_records],
        }
        hardening_log = HardeningLog(
            initial_blueprint_id=blueprint.blueprint_id,
            hardened_blueprint_id=current_blueprint.blueprint_id,
            initial_survival_rate=initial_report.survival_rate,
            final_survival_rate=current_survival_rate,
            pass_count=pass_count,
            applied_patches=all_applied_patches,
            pass_records=pass_records,
            log_hash=compute_sha256(log_payload),
            created_at=datetime.now(timezone.utc),
        )
        await self.repo.save_hardening_log(hardening_log)

        return HardeningLoopResult(
            initial_blueprint_id=blueprint.blueprint_id,
            hardened_blueprint_id=current_blueprint.blueprint_id,
            initial_survival_rate=initial_report.survival_rate,
            final_survival_rate=current_survival_rate,
            threshold_met=threshold_met,
            total_passes=pass_count,
            applied_patches=all_applied_patches,
            pass_records=pass_records,
            hardening_log=hardening_log,
        )

    def format_human_readable_log(self, log: HardeningLog) -> str:
        """
        Renders a human-readable summary of the hardening log matching the PromptForge spec.
        Example format:
        Survival 14/20 (70%) → 18/20 (90%) after 1 hardening pass
          Patch 1: added tool-policy rule "refund > $500 → require_manager_approval"
          Patch 2: tightened system prompt §5 (role-hijack defense)
        """
        lines = []
        lines.append("=" * 72)
        lines.append("PROMPTFORGE HARDENING REPORT")
        lines.append("=" * 72)
        lines.append(f"Initial Blueprint  : {log.initial_blueprint_id}")
        lines.append(f"Hardened Blueprint : {log.hardened_blueprint_id}")
        lines.append(
            f"Survival Progression: {log.initial_survival_rate:.1%} → {log.final_survival_rate:.1%} "
            f"after {log.pass_count} hardening pass{'es' if log.pass_count != 1 else ''}"
        )
        if log.log_hash:
            lines.append(f"Integrity Hash     : {log.log_hash}")
        lines.append(f"Timestamp (UTC)    : {log.created_at.isoformat()}")
        lines.append("-" * 72)

        lines.append(f"APPLIED SURGICAL PATCHES ({len(log.applied_patches)}):")
        if not log.applied_patches:
            lines.append("  (No patches applied — agent met security threshold without modification)")
        else:
            for i, p in enumerate(log.applied_patches, start=1):
                target_str = f"[{p.target.upper()}]"
                if p.target_name:
                    target_str += f" {p.target_name}"
                lines.append(f"  Patch {i} ({p.patch_id}): {target_str}")
                lines.append(f"    Category  : {p.category}")
                lines.append(f"    Rationale : {p.rationale}")
                diff_preview = p.diff.strip().splitlines()
                if diff_preview:
                    lines.append("    Diff:")
                    for dl in diff_preview[:5]:
                        lines.append(f"      {dl}")
                    if len(diff_preview) > 5:
                        lines.append(f"      ... ({len(diff_preview) - 5} more lines)")

        if log.pass_records:
            lines.append("-" * 72)
            lines.append("PASS BREAKDOWN:")
            for pr in log.pass_records:
                lines.append(
                    f"  Pass {pr.pass_number}: Targeted [{', '.join(pr.categories_targeted)}] | "
                    f"Survival: {pr.survival_rate_before:.1%} → {pr.survival_rate_after:.1%} "
                    f"({pr.sessions_run} sessions, {len(pr.patches_applied)} patches)"
                )
        lines.append("=" * 72)
        return "\n".join(lines)

