import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ..core.delimiting import delimit_untrusted_input
from ..core.errors import BuilderPolicyViolationException
from ..core.guardrail_prober import validate_guardrail_with_probes
from ..core.hash_chain import compute_sha256
from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import (
    AgentBlueprint,
    FewShotConversation,
    FewShotMessage,
    Guardrail,
    ProvenanceRegistryEntry,
    ToolSchema,
)
from ..models.chain_outputs import (
    FewShotExamplesOutput,
    GuardrailsOutput,
    SystemPromptOutput,
    ToolSchemaOutput,
)
from ..models.spec import AgentSpec
from ..models.test_set import GeneratedTestSuite, TestCase
from .shield_service import ShieldService

logger = logging.getLogger("promptforge.services.forge")

class ForgeService:
    """Orchestrates Forge lifecycle stages: Intent Decomposition, Spec Confirmation, and Blueprint Assembly."""

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None,
        shield_service: Optional[ShieldService] = None
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.registry = get_prompt_registry()
        self.shield_service = shield_service or ShieldService(repo=self.repo, llm=self.llm)

    async def decompose_intent(
        self,
        description: str,
        tenant_id: str = "tenant-default",
        model: str = "gpt-4o"
    ) -> AgentSpec:
        """
        Executes Chain 1: Decomposes natural language description into an AgentSpec.
        Validates JSON structure with retry and persists spec to DB.
        """
        safe_description = delimit_untrusted_input(description, tag="untrusted_user_description")
        prompt = self.registry.render("chain_1_intent_decomposition", description=safe_description)
        spec = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=AgentSpec,
            model=model
        )
        spec.raw_description = description
        spec.tenant_id = tenant_id

        # Persist to storage
        await self.repo.save_spec(spec)
        logger.info(f"Spec {spec.spec_id} successfully decomposed and saved for tenant {tenant_id}.")
        return spec

    async def confirm_spec(self, spec_update: AgentSpec) -> AgentSpec:
        """
        Saves updated, confirmed capabilities from the user (Stage 0).
        Enforces Step 58: Builder-side abuse policy and impersonation refusal.
        """
        builder_eval = self.shield_service.evaluate_builder_policy(spec_update)
        if builder_eval.impersonation_detected:
            raise BuilderPolicyViolationException(
                message=f"Impersonation Refusal: Spec targets or impersonates protected entity '{builder_eval.impersonated_entity}'.",
                guidance=builder_eval.refusal_guidance,
                details={"impersonated_entity": builder_eval.impersonated_entity}
            )

        if "credential_harvesting" in builder_eval.high_risk_capabilities:
            raise BuilderPolicyViolationException(
                message="Builder Abuse Policy Violation: Spec requests harvesting caller credentials or passwords.",
                guidance=builder_eval.refusal_guidance,
                details={"high_risk_capabilities": builder_eval.high_risk_capabilities}
            )

        spec_update.confirmed = True
        await self.repo.save_spec(spec_update)
        logger.info(f"Spec {spec_update.spec_id} confirmed by user.")
        return spec_update

    async def generate_test_suite(
        self,
        spec: AgentSpec,
        model: str = "openai/gpt-oss-120b"
    ) -> GeneratedTestSuite:
        """
        Executes Chain 14: Synthesizes gold cases, edge cases, and incorporates user gold Q&A.
        Uses an independent model persona from the generator to prevent circular evaluation.
        Model defaults to the Groq-hosted workhorse so this chain runs live without requiring
        a separate Anthropic API key.
        """
        user_gold_str = json.dumps(spec.user_gold_qa) if spec.user_gold_qa else "None provided"
        spec_json = spec.model_dump_json(indent=2)
        prompt = self.registry.render(
            "chain_14_test_set_generation",
            spec_json=spec_json,
            user_gold_qa=user_gold_str
        )
        suite = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=GeneratedTestSuite,
            model=model
        )
        suite.spec_id = spec.spec_id

        # Inject user-gold Q&A explicitly tagged as source="user" in order
        if spec.user_gold_qa:
            user_cases = []
            for i, qa in enumerate(spec.user_gold_qa):
                q = qa.get("question", "").strip()
                a = qa.get("answer", "").strip()
                if q:
                    user_cases.append(TestCase(
                        case_id=f"user-gold-{i+1}",
                        question=q,
                        expected_answer=a,
                        category="user_gold",
                        source="user"
                    ))
            suite.gold_cases = user_cases + suite.gold_cases

        suite.user_supplied_count = sum(1 for c in suite.gold_cases if c.source == "user")
        suite.generated_count = len(suite.gold_cases) - suite.user_supplied_count + len(suite.edge_cases)
        suite.total_cases = len(suite.gold_cases) + len(suite.edge_cases)

        logger.info(
            f"Generated test suite {suite.suite_id} for spec {spec.spec_id}: "
            f"{suite.user_supplied_count} user cases, {suite.generated_count} generated cases."
        )
        return suite

    async def generate_system_prompt(
        self,
        spec: AgentSpec,
        model: str = "gpt-4o"
    ) -> SystemPromptOutput:
        """
        Executes Chain 2: Synthesizes a 400-800 word CRISPE system prompt based on confirmed spec.
        """
        spec_json = delimit_untrusted_input(spec.model_dump_json(indent=2), tag="untrusted_spec")
        prompt = self.registry.render(
            "chain_2_system_prompt_generation",
            spec_json=spec_json
        )
        res = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=SystemPromptOutput,
            model=model
        )
        words = len(res.system_prompt.split())
        res.word_count = words
        logger.info(f"Generated system prompt for spec {spec.spec_id} ({words} words).")
        return res

    async def generate_tools(
        self,
        spec: AgentSpec,
        model: str = "gpt-4o"
    ) -> List[ToolSchema]:
        """
        Executes Chain 3: Generates OpenAI-compatible function calling schemas with endpoint bindings.
        """
        spec_json = delimit_untrusted_input(spec.model_dump_json(indent=2), tag="untrusted_spec")
        prompt = self.registry.render(
            "chain_3_tool_schema_generation",
            spec_json=spec_json
        )
        output = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=ToolSchemaOutput,
            model=model
        )
        tools = [ToolSchema.model_validate(t) for t in output.tools]
        logger.info(f"Generated {len(tools)} tools for spec {spec.spec_id}.")
        return tools

    async def generate_guardrails(
        self,
        spec: AgentSpec,
        model: str = "gpt-4o"
    ) -> List[Guardrail]:
        """
        Executes Chain 4: Generates 10–18 guardrails in two layers (middleware & semantic)
        and validates every guardrail with 3 positive + 3 negative unit probes.
        """
        spec_json = delimit_untrusted_input(spec.model_dump_json(indent=2), tag="untrusted_spec")
        prompt = self.registry.render(
            "chain_4_guardrail_generation",
            spec_json=spec_json
        )
        output = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=GuardrailsOutput,
            model=model
        )
        validated_guardrails: List[Guardrail] = []
        for g_data in output.guardrails:
            rail = Guardrail(
                name=g_data.name,
                layer=g_data.layer,
                pattern_or_rule=g_data.pattern_or_rule,
                action=g_data.action
            )
            passed, logs = validate_guardrail_with_probes(rail)
            if passed:
                rail.probes_passed = True
                validated_guardrails.append(rail)
            else:
                logger.warning(f"Guardrail '{rail.name}' rejected by probe validation: {logs}")

        logger.info(f"Generated and validated {len(validated_guardrails)} guardrails for spec {spec.spec_id}.")
        return validated_guardrails

    async def generate_few_shot_examples(
        self,
        spec: AgentSpec,
        model: str = "gpt-4o"
    ) -> List[FewShotConversation]:
        """
        Executes Chain 5: Generates 5 canonical few-shot exemplar conversations
        (happy_path, edge_case, adversarial_block, tool_use, escalation).
        """
        spec_json = delimit_untrusted_input(spec.model_dump_json(indent=2), tag="untrusted_spec")
        prompt = self.registry.render(
            "chain_5_few_shot_generation",
            spec_json=spec_json
        )
        output = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=FewShotExamplesOutput,
            model=model
        )
        conversations: List[FewShotConversation] = []
        for ex in output.examples:
            msgs = [
                FewShotMessage(role=m.get("role", "user"), content=m.get("content", ""))
                for m in ex.messages
            ]
            conversations.append(FewShotConversation(
                scenario_type=ex.scenario_type,
                messages=msgs
            ))
        logger.info(f"Generated {len(conversations)} few-shot exemplar conversations for spec {spec.spec_id}.")
        return conversations

    async def assemble_blueprint(
        self,
        spec: AgentSpec,
        model: str = "gpt-4o"
    ) -> AgentBlueprint:
        """
        Combines outputs of Chains 2–5 into one persisted AgentBlueprint with cryptographic SHA-256 fingerprint.
        1. Chain 2: CRISPE System Prompt
        2. Chain 3: OpenAI-compatible Tool Schemas
        3. Chain 4: Two-layer Guardrails with unit probe validation
        4. Chain 5: Canonical Few-Shot Exemplars
        5. Fold exemplars into system prompt
        6. Compute blueprint hash
        7. Persist blueprint in database
        """
        # Parallelize execution of Chains 2–5 via asyncio.gather to meet the ~10–15s Forge timing target
        sys_prompt_output, tools, guardrails, few_shots = await asyncio.gather(
            self.generate_system_prompt(spec, model=model),
            self.generate_tools(spec, model=model),
            self.generate_guardrails(spec, model=model),
            self.generate_few_shot_examples(spec, model=model),
        )

        # 5. Fold few-shot examples into the system prompt
        exemplars_block = format_few_shot_examples_block(few_shots)
        assembled_system_prompt = f"{sys_prompt_output.system_prompt.strip()}\n{exemplars_block}"

        # 5b. Evaluate Tool Schemas for High-Risk Capabilities (Step 58)
        review_required = False
        review_flags: List[str] = []
        for t in tools:
            t_str = json.dumps(t.model_dump(), default=str).lower()
            if any(k in t_str for k in ["password", "credential", "seed_phrase", "pin", "harvest"]):
                t.high_risk = True
                t.high_risk_category = "credential_harvesting"
                review_required = True
                review_flags.append(f"tool:{t.name}:credential_harvesting")
            elif any(k in t_str for k in ["arbitrary_code", "execute_shell", "root_terminal", "bash"]):
                t.high_risk = True
                t.high_risk_category = "arbitrary_code_execution"
                review_required = True
                review_flags.append(f"tool:{t.name}:arbitrary_code_execution")
            elif any(k in t_str for k in ["wire_transfer", "drain_funds", "unrestricted_transfer"]):
                t.high_risk = True
                t.high_risk_category = "unrestricted_money_transfer"
                review_required = True
                review_flags.append(f"tool:{t.name}:unrestricted_money_transfer")

        # 5c. Provenance Watermark & Registry Entry (Step 59)
        blueprint_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        watermark = f"pf:v1:{blueprint_id[:8]}:{spec.tenant_id}:{created_at.strftime('%Y%m%d%H%M%S')}"
        prompt_marker = f"\n\n<!-- [PromptForge Provenance: agent_id={blueprint_id} forger_id={spec.tenant_id} watermark={watermark}] -->"
        final_system_prompt = f"{assembled_system_prompt}{prompt_marker}"

        provenance_entry = ProvenanceRegistryEntry(
            agent_id=blueprint_id,
            blueprint_id=blueprint_id,
            forger_id=spec.tenant_id,
            agent_name=spec.agent_name,
            watermark=watermark,
            system_prompt_marker=prompt_marker.strip(),
            registered_at=created_at,
            provenance_hash=compute_sha256({
                "agent_id": blueprint_id,
                "forger_id": spec.tenant_id,
                "watermark": watermark,
                "spec_id": spec.spec_id,
            }),
        )

        # 6. Build Blueprint
        blueprint = AgentBlueprint(
            blueprint_id=blueprint_id,
            spec_id=spec.spec_id,
            tenant_id=spec.tenant_id,
            agent_name=spec.agent_name,
            system_prompt=final_system_prompt,
            tools=tools,
            guardrails=guardrails,
            few_shot_examples=few_shots,
            provenance_watermark=watermark,
            provenance_record=provenance_entry,
            review_required=review_required,
            review_flags=review_flags,
            created_at=created_at,
        )

        # 7. Compute deterministic SHA-256 hash
        blueprint_content = {
            "spec_id": blueprint.spec_id,
            "tenant_id": blueprint.tenant_id,
            "agent_name": blueprint.agent_name,
            "system_prompt": blueprint.system_prompt,
            "tools": [t.model_dump() for t in blueprint.tools],
            "guardrails": [g.model_dump() for g in blueprint.guardrails],
            "few_shot_examples": [f.model_dump() for f in blueprint.few_shot_examples],
            "provenance_watermark": blueprint.provenance_watermark,
        }
        blueprint.blueprint_hash = compute_sha256(blueprint_content)

        # 8. Persist to DB and Registry
        await self.repo.save_blueprint(blueprint)
        await self.repo.save_registry_entry(provenance_entry)
        logger.info(
            f"Assembled and persisted blueprint {blueprint.blueprint_id} "
            f"for spec {spec.spec_id} with hash {blueprint.blueprint_hash} and registry entry {provenance_entry.registry_id}"
        )

        # 9. Stage 4: SHIELD (Policy Generation for runtime middleware gates B, D, E)
        try:
            await self.shield_service.generate_policy(spec=spec, blueprint=blueprint, persist=True)
            logger.info(f"Generated and persisted SHIELD policy for spec {spec.spec_id}")
        except Exception as e:
            logger.warning(f"Could not generate SHIELD policy during blueprint assembly: {e}")

        # 10. Record Forge complete milestone in cryptographic hash chain
        try:
            from .audit_service import AuditTrailService
            await AuditTrailService(repo=self.repo).record_forge_complete(blueprint)
        except Exception as e:
            logger.warning(f"Could not record forge audit event for blueprint {blueprint.blueprint_id}: {e}")

        return blueprint



def format_few_shot_examples_block(examples: List[FewShotConversation]) -> str:
    """Formats few-shot exemplar dialogues into a readable block to fold into system prompts."""
    lines = ["\n\n### Canonical Few-Shot Exemplar Dialogues"]
    for i, ex in enumerate(examples, 1):
        clean_scenario = ex.scenario_type.replace("_", " ").title()
        lines.append(f"\n#### Exemplar {i} ({clean_scenario}):")
        for msg in ex.messages:
            lines.append(f"**{msg.role.capitalize()}**: {msg.content}")
    return "\n".join(lines)

