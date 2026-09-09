import json
import logging
import uuid
from typing import AsyncGenerator, Callable, List, Optional, Tuple

from ..core.concurrent_runner import run_concurrent_sessions
from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..core.quality_gate import AttackQualityGate, QualityGateResult
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.redteam import (
    AttackTurnRecord,
    ExecutedAttackTranscript,
    GeneratedAttackCase,
    GeneratedAttacksBatch,
)
from ..models.runtime import ChatMessage, ChatRequest
from .runtime_service import AgentRuntimeService
from .seed_corpus_service import SeedCorpusService, get_seed_corpus_service

logger = logging.getLogger("promptforge.services.redteam")


class RedTeamService:
    """
    Orchestrates the PromptForge Red Team engine:
    1. Persona-driven attack generation (Chain 6) tailored specifically to target agents.
    2. Attack quality gating (target verification, embedding deduplication, difficulty calibration).
    3. Concurrent multi-turn attack execution (Chain 7).
    4. Attack judgment and evidence-backed evaluation (Chain 8).
    5. RedTeamReport synthesis and live verdict streaming.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None,
        seed_service: Optional[SeedCorpusService] = None,
        quality_gate: Optional[AttackQualityGate] = None
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.registry = get_prompt_registry()
        self.seed_service = seed_service or get_seed_corpus_service()
        self.quality_gate = quality_gate or AttackQualityGate()


    async def generate_attacks_for_persona(
        self,
        blueprint: AgentBlueprint,
        persona: str,
        category: Optional[str] = None,
        count: int = 3,
        model: str = "gpt-4o"
    ) -> List[GeneratedAttackCase]:
        """
        Executes Chain 6: Generates targeted attack cases for a specific attacker persona,
        seeded by matching patterns from the seed corpus, and strictly tailored to the agent's
        declared capabilities, boundaries, and tools.
        """
        # Retrieve relevant seed patterns for inspiration
        seeds = self.seed_service.get_sample_seeds(count=count, category=category)
        seed_examples_json = json.dumps(seeds, indent=2)

        spec_data = {
            "agent_name": blueprint.agent_name,
            "system_prompt_summary": blueprint.system_prompt[:300] + "...",
            "declared_boundaries": [g.pattern_or_rule for g in blueprint.guardrails if g.layer == "middleware"],
            "semantic_policies": [g.name for g in blueprint.guardrails if g.layer == "semantic"]
        }
        spec_json = json.dumps(spec_data, indent=2)
        tools_json = json.dumps([t.model_dump() for t in blueprint.tools], indent=2)

        prompt = self.registry.render(
            "chain_6_attack_generation",
            persona=persona,
            spec_json=spec_json,
            tools_json=tools_json,
            seed_examples_json=seed_examples_json
        )

        batch = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=GeneratedAttacksBatch,
            model=model
        )

        # Ensure all attacks are tagged with the requested persona and have generated IDs
        for atk in batch.attacks:
            if not atk.attacker_persona:
                atk.attacker_persona = persona

        logger.info(
            f"Generated {len(batch.attacks)} targeted attacks for persona '{persona}' "
            f"against blueprint '{blueprint.blueprint_id}'."
        )
        return batch.attacks

    async def generate_full_campaign(
        self,
        blueprint: AgentBlueprint,
        attacks_per_persona: int = 2,
        model: str = "gpt-4o"
    ) -> List[GeneratedAttackCase]:
        """
        Generates a comprehensive multi-persona attack campaign spanning all 5 attacker archetypes:
        1. Social Engineer
        2. Jailbreaker
        3. Data Extractor
        4. Tool Abuser
        5. Multilingual Attacker
        """
        personas = [
            ("Social Engineer", "social_engineering"),
            ("Jailbreaker", "prompt_injection"),
            ("Data Extractor", "system_extraction"),
            ("Tool Abuser", "tool_abuse"),
            ("Multilingual Attacker", "multilingual_evasion")
        ]

        campaign_attacks: List[GeneratedAttackCase] = []
        for persona_name, cat in personas:
            attacks = await self.generate_attacks_for_persona(
                blueprint=blueprint,
                persona=persona_name,
                category=cat,
                count=attacks_per_persona,
                model=model
            )
            campaign_attacks.extend(attacks)

        logger.info(
            f"Assembled full campaign of {len(campaign_attacks)} attacks across {len(personas)} personas "
            f"for blueprint {blueprint.blueprint_id}."
        )
        return campaign_attacks

    def apply_quality_gate(
        self,
        blueprint: AgentBlueprint,
        attacks: List[GeneratedAttackCase]
    ) -> QualityGateResult:
        """
        Applies target surface verification, embedding deduplication, and difficulty mix calibration.
        """
        return self.quality_gate.evaluate_batch(blueprint, attacks)

    async def generate_gated_campaign(
        self,
        blueprint: AgentBlueprint,
        attacks_per_persona: int = 4,
        model: str = "gpt-4o"
    ) -> QualityGateResult:
        """
        Generates a comprehensive campaign across all 5 personas and filters
        all attacks through the Attack Quality Gate, guaranteeing diversity and difficulty mix.
        """
        raw_attacks = await self.generate_full_campaign(
            blueprint=blueprint,
            attacks_per_persona=attacks_per_persona,
            model=model
        )
        return self.apply_quality_gate(blueprint, raw_attacks)

    async def execute_attack_session(
        self,
        blueprint: AgentBlueprint,
        attack: GeneratedAttackCase,
        runtime_service: Optional[AgentRuntimeService] = None
    ) -> ExecutedAttackTranscript:
        """
        Executes a stateful multi-turn attack session against the target agent runtime.
        Carries conversational state, simulated tool calls, and captures failure modes.
        """
        runtime = runtime_service or AgentRuntimeService(repo=self.repo, llm=self.llm)
        session_id = f"redteam-sess-{uuid.uuid4().hex[:8]}"

        history: List[ChatMessage] = []
        turn_records: List[AttackTurnRecord] = []
        was_blocked = False
        triggered_guardrail: Optional[str] = None
        final_reply = ""

        # Classify stateful failure mode
        vec_lower = attack.attack_vector.lower()
        if "poison" in vec_lower or "tool_result" in vec_lower:
            failure_mode = "tool_result_poisoning"
        elif "cumulative" in vec_lower or "trust" in vec_lower:
            failure_mode = "cumulative_injection"
        elif "erosion" in vec_lower or "gradual" in vec_lower:
            failure_mode = "gradual_instruction_erosion"
        else:
            failure_mode = "direct_probe"

        for i, turn in enumerate(attack.turns, 1):
            chat_req = ChatRequest(
                message=turn.prompt,
                history=history,
                session_id=session_id
            )
            chat_res = await runtime.chat(blueprint.blueprint_id, chat_req)

            final_reply = chat_res.response
            if chat_res.blocked:
                was_blocked = True
                triggered_guardrail = chat_res.guardrail_triggered

            turn_records.append(AttackTurnRecord(
                turn_index=i,
                user_prompt=turn.prompt,
                agent_response=chat_res.response,
                tool_calls=[tc.model_dump() for tc in chat_res.tool_calls],
                blocked=chat_res.blocked,
                guardrail_triggered=chat_res.guardrail_triggered
            ))

            # Maintain conversational state across turns
            history.append(ChatMessage(role="user", content=turn.prompt))
            history.append(ChatMessage(role="assistant", content=chat_res.response))

            # If blocked by deterministic middleware, further turns are stopped
            if chat_res.blocked:
                break

        return ExecutedAttackTranscript(
            session_id=session_id,
            attack_id=attack.attack_id,
            blueprint_id=blueprint.blueprint_id,
            attacker_persona=attack.attacker_persona,
            category=attack.category,
            attack_vector=attack.attack_vector,
            target_surface=attack.target_surface,
            target_element=attack.target_element,
            difficulty=attack.difficulty,
            is_multi_turn=len(attack.turns) > 1,
            failure_mode=failure_mode,
            turns=turn_records,
            final_response=final_reply,
            was_blocked_any_turn=was_blocked,
            guardrail_triggered=triggered_guardrail
        )

    async def stream_attack_execution(
        self,
        blueprint: AgentBlueprint,
        attacks: List[GeneratedAttackCase],
        concurrency: int = 8,
        runtime_service: Optional[AgentRuntimeService] = None,
        on_progress: Optional[Callable[[int, ExecutedAttackTranscript], None]] = None
    ) -> AsyncGenerator[Tuple[int, ExecutedAttackTranscript], None]:
        """
        Executes attacks concurrently via the concurrent runner, streaming results as they finish.
        """
        runtime = runtime_service or AgentRuntimeService(repo=self.repo, llm=self.llm)

        def make_task(atk: GeneratedAttackCase):
            async def task_fn():
                return await self.execute_attack_session(blueprint, atk, runtime_service=runtime)
            return task_fn

        task_factories = [make_task(atk) for atk in attacks]

        async for item in run_concurrent_sessions(
            tasks=task_factories,
            concurrency=concurrency,
            on_result=on_progress
        ):
            yield item

    async def execute_attack_batch_concurrently(
        self,
        blueprint: AgentBlueprint,
        attacks: List[GeneratedAttackCase],
        concurrency: int = 8,
        runtime_service: Optional[AgentRuntimeService] = None
    ) -> List[ExecutedAttackTranscript]:
        """
        Runs an entire attack batch concurrently and returns all executed transcripts.
        """
        results: List[ExecutedAttackTranscript] = []
        async for _, transcript in self.stream_attack_execution(
            blueprint=blueprint,
            attacks=attacks,
            concurrency=concurrency,
            runtime_service=runtime_service
        ):
            results.append(transcript)
        return results


