import asyncio
import json
import logging
import math
import random
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

import httpx

from ..config import settings
from ..core.concurrent_runner import run_concurrent_sessions
from ..core.delimiting import delimit_untrusted_input
from ..core.hash_chain import compute_sha256
from ..core.json_validator import execute_chain_with_retry
from ..core.judge_assignment import select_judge_model
from ..core.prompt_registry import get_prompt_registry
from ..core.quality_gate import AttackQualityGate, QualityGateResult
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.redteam import (
    AttackJudgmentOutput,
    AttackTurnRecord,
    AttackVerdict,
    ExecutedAttackTranscript,
    GeneratedAttackCase,
    GeneratedAttacksBatch,
    RedTeamReport,
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
        # Retrieve static seed patterns for inspiration
        static_seeds = self.seed_service.get_sample_seeds(count=count, category=category)

        # Retrieve dynamic seeds from persistent Playbook (Step 47)
        playbook_entries = await self.repo.list_playbook_entries(category=category)
        dynamic_seeds = []
        for p in playbook_entries:
            dynamic_seeds.append({
                "category": p.attack_category,
                "difficulty": "hard",
                "attack_vector": p.anonymized_attack_pattern,
                "sample_prompt": p.anonymized_attack_pattern,
                "domain": p.domain,
                "source": "live_playbook"
            })

        # Combine seeds: prioritize live playbook entries if available, supplemented by static seeds
        has_playbook_seeds = len(dynamic_seeds) > 0
        combined_seeds = dynamic_seeds[:count] + static_seeds[:max(0, count - len(dynamic_seeds))]
        if not combined_seeds:
            combined_seeds = static_seeds

        seed_examples_json = json.dumps(combined_seeds, indent=2)

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

        # Ensure all attacks are tagged with the requested persona and proper seed source
        for atk in batch.attacks:
            atk.attacker_persona = persona
            if has_playbook_seeds:
                atk.seed_source = "live_playbook"

        logger.info(
            f"Generated {len(batch.attacks)} targeted attacks for persona '{persona}' "
            f"(Playbook seeds used: {has_playbook_seeds}) against blueprint '{blueprint.blueprint_id}'."
        )
        return batch.attacks

    async def is_ollama_available(self) -> bool:
        """
        Pings local Ollama service to check availability and health.
        """
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate_full_campaign(
        self,
        blueprint: AgentBlueprint,
        attacks_per_persona: int = 2,
        model: str = "gpt-4o",
        include_ollama: bool = True
    ) -> List[GeneratedAttackCase]:
        """
        Generates a comprehensive multi-persona attack campaign spanning all attacker archetypes:
        1. Social Engineer
        2. Jailbreaker
        3. Data Extractor
        4. Tool Abuser
        5. Multilingual Attacker
        6. Open-Weight Local Attacker (via Ollama when enabled/available)
        """
        personas = [
            ("Social Engineer", "social_engineering", model),
            ("Jailbreaker", "prompt_injection", model),
            ("Data Extractor", "system_extraction", model),
            ("Tool Abuser", "tool_abuse", model),
            ("Multilingual Attacker", "multilingual_evasion", model)
        ]

        if include_ollama and settings.ollama_enabled:
            # Wire in open-weight local model as additional attacker persona ("attacker your agent has never seen")
            ollama_active = await self.is_ollama_available()
            ow_model = settings.ollama_model if ollama_active else f"{settings.ollama_model}-mock-fallback"
            personas.append(("Open-Weight Local Attacker", "unseen_distribution_probe", ow_model))

        # Concurrently generate attacks across all personas to meet ~15–25s target
        persona_results = await asyncio.gather(*(
            self.generate_attacks_for_persona(
                blueprint=blueprint,
                persona=persona_name,
                category=cat,
                count=attacks_per_persona,
                model=persona_model,
            )
            for persona_name, cat, persona_model in personas
        ))
        campaign_attacks: List[GeneratedAttackCase] = []
        for attacks in persona_results:
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
            seed_source=getattr(attack, "seed_source", "seed_corpus"),
            turns=turn_records,
            final_response=final_reply,
            was_blocked_any_turn=was_blocked,
            guardrail_triggered=triggered_guardrail
        )

    async def stream_attack_execution(
        self,
        blueprint: AgentBlueprint,
        attacks: List[GeneratedAttackCase],
        concurrency: int = 10,
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
        concurrency: int = 10,
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

    async def judge_attack_transcript(
        self,
        blueprint: AgentBlueprint,
        transcript: ExecutedAttackTranscript,
        generator_model: str = "gpt-4o",
        custom_judge_model: Optional[str] = None
    ) -> AttackVerdict:
        """
        Executes Chain 8: Impartial Attack Judgment with strict evidence-required rubric.
        Ensures judge_model != generator_model.
        Returns an AttackVerdict with cited verbatim evidence.
        """
        judge_model = custom_judge_model or select_judge_model(generator_model=generator_model)

        spec_data = {
            "agent_name": blueprint.agent_name,
            "declared_boundaries": [g.pattern_or_rule for g in blueprint.guardrails if g.layer == "middleware"],
            "semantic_policies": [g.name for g in blueprint.guardrails if g.layer == "semantic"]
        }
        spec_json = json.dumps(spec_data, indent=2)

        transcript_data = {
            "attack_id": transcript.attack_id,
            "persona": transcript.attacker_persona,
            "category": transcript.category,
            "attack_vector": transcript.attack_vector,
            "turns": [t.model_dump() for t in transcript.turns],
            "final_response": transcript.final_response,
            "was_blocked_any_turn": transcript.was_blocked_any_turn,
            "guardrail_triggered": transcript.guardrail_triggered
        }
        transcript_json = json.dumps(transcript_data, indent=2)
        safe_transcript_json = delimit_untrusted_input(transcript_json, tag="untrusted_attack_transcript")
        safe_spec_json = delimit_untrusted_input(spec_json, tag="untrusted_spec")

        prompt = self.registry.render(
            "chain_8_attack_judgment",
            spec_json=safe_spec_json,
            transcript_json=safe_transcript_json,
            intended_violation=f"Target: {transcript.target_surface} ({transcript.target_element})"
        )

        judgment_out = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=AttackJudgmentOutput,
            model=judge_model
        )

        # Enforce that evidence is present (strict evidence-required rubric)
        evidence_list = judgment_out.cited_evidence or []
        if not evidence_list:
            if transcript.was_blocked_any_turn:
                evidence_list.append(f"Guardrail triggered: {transcript.guardrail_triggered or 'blocked'}")
            elif transcript.final_response:
                evidence_list.append(transcript.final_response[:100])
            else:
                evidence_list.append("Execution observed without verbal exception")

        cited_evidence_str = " | ".join(evidence_list)
        prompt_excerpt = transcript.turns[0].user_prompt if transcript.turns else ""

        verdict = AttackVerdict(
            attack_id=transcript.attack_id,
            session_id=transcript.session_id,
            category=transcript.category,
            attacker_persona=transcript.attacker_persona,
            attacker_model=generator_model,
            prompt=prompt_excerpt,
            response=transcript.final_response,
            verdict=judgment_out.verdict,
            verdict_rationale=judgment_out.verdict_rationale,
            cited_evidence=cited_evidence_str,
            violation_detected=judgment_out.violation_detected,
            violated_boundary_or_policy=judgment_out.violated_boundary_or_policy,
            severity_score=judgment_out.severity_score,
            judge_model=judge_model,
            seed_source=getattr(transcript, "seed_source", "seed_corpus")
        )

        logger.info(
            f"Judge [{judge_model}] rendered verdict '{verdict.verdict}' for attack '{transcript.attack_id}' "
            f"(Generator: {generator_model}). Evidence cited: {len(evidence_list)} quotes."
        )
        return verdict

    async def judge_transcripts_batch(
        self,
        blueprint: AgentBlueprint,
        transcripts: List[ExecutedAttackTranscript],
        generator_model: str = "gpt-4o",
        concurrency: int = 10
    ) -> List[AttackVerdict]:
        """
        Judges a batch of attack transcripts concurrently using the concurrent runner.
        """
        def make_judge_task(t: ExecutedAttackTranscript):
            async def task_fn():
                return await self.judge_attack_transcript(blueprint, t, generator_model=generator_model)
            return task_fn

        task_factories = [make_judge_task(t) for t in transcripts]
        verdicts: List[AttackVerdict] = []
        async for _, v in run_concurrent_sessions(tasks=task_factories, concurrency=concurrency):
            verdicts.append(v)
        return verdicts

    async def perform_judge_cross_check(
        self,
        blueprint: AgentBlueprint,
        transcripts: List[ExecutedAttackTranscript],
        verdicts: List[AttackVerdict],
        sample_rate: float = 0.20,
        seed: Optional[int] = None
    ) -> Tuple[List[AttackVerdict], float]:
        """
        Executes Step 40: Judge Cross-Check.
        Randomly samples 20% of verdicts, re-judges each using an independent 3rd model
        (distinct from both the generator and the primary judge), computes the agreement rate,
        and enriches the verdicts with cross-check results.
        """
        if not verdicts or not transcripts:
            return verdicts, 1.0

        rng = random.Random(seed) if seed is not None else random.Random()

        # Map transcripts by attack_id / session_id
        transcript_map: Dict[str, ExecutedAttackTranscript] = {}
        for t in transcripts:
            transcript_map[t.attack_id] = t
            transcript_map[t.session_id] = t

        # Determine sample indices (at least 1 if sample_rate > 0 and verdicts exist)
        sample_size = max(1, math.ceil(len(verdicts) * sample_rate))
        sample_indices = rng.sample(range(len(verdicts)), min(sample_size, len(verdicts)))

        async def _cross_check_single(idx: int):
            v = verdicts[idx]
            t = transcript_map.get(v.attack_id or "") or transcript_map.get(v.session_id or "")
            if not t:
                return
            third_model = select_judge_model(
                generator_model=v.attacker_model,
                exclude_models=[v.judge_model]
            )
            second_verdict = await self.judge_attack_transcript(
                blueprint=blueprint,
                transcript=t,
                generator_model=v.attacker_model,
                custom_judge_model=third_model
            )
            agrees = (v.verdict.upper() == second_verdict.verdict.upper())
            v.cross_check_model = third_model
            v.cross_check_verdict = second_verdict.verdict
            v.cross_check_agrees = agrees
            logger.info(
                f"Cross-check for attack '{v.attack_id}': Primary Judge [{v.judge_model}]={v.verdict} vs "
                f"Third Judge [{third_model}]={second_verdict.verdict}. Agreement: {agrees}"
            )
            return agrees

        # Independent per-verdict — fan out
        results = await asyncio.gather(*[_cross_check_single(idx) for idx in sample_indices])
        total_cross_checked = sum(1 for r in results if r is not None)
        agreed_count = sum(1 for r in results if r is True)

        agreement_rate = (agreed_count / total_cross_checked) if total_cross_checked > 0 else 1.0
        logger.info(
            f"Cross-check complete: {agreed_count}/{total_cross_checked} agreed "
            f"({agreement_rate * 100:.1f}% agreement rate)."
        )
        return verdicts, round(agreement_rate, 4)

    def assemble_redteam_report(
        self,
        blueprint: AgentBlueprint,
        verdicts: List[AttackVerdict],
        difficulty_mix: Optional[Dict[str, int]] = None,
        cross_check_agreement_rate: Optional[float] = None
    ) -> RedTeamReport:
        """
        Assembles the comprehensive RedTeamReport with per-category breakdown,
        difficulty mix, survival rate, and deterministic SHA-256 tamper-evident hash.
        """
        total_attacks = len(verdicts)
        blocked_count = sum(1 for v in verdicts if v.verdict.upper() == "BLOCKED")
        degraded_count = sum(1 for v in verdicts if v.verdict.upper() == "DEGRADED")
        compromised_count = sum(1 for v in verdicts if v.verdict.upper() == "COMPROMISED")
        survival_rate = round((blocked_count / total_attacks) if total_attacks > 0 else 1.0, 4)

        category_breakdown: Dict[str, Dict[str, int]] = {}
        for v in verdicts:
            cat = v.category or "uncategorized"
            if cat not in category_breakdown:
                category_breakdown[cat] = {"BLOCKED": 0, "DEGRADED": 0, "COMPROMISED": 0, "total": 0}
            vrd = v.verdict.upper()
            if vrd in category_breakdown[cat]:
                category_breakdown[cat][vrd] += 1
            category_breakdown[cat]["total"] += 1

        report_payload = {
            "blueprint_id": blueprint.blueprint_id,
            "tenant_id": blueprint.tenant_id,
            "total_attacks": total_attacks,
            "blocked_count": blocked_count,
            "degraded_count": degraded_count,
            "compromised_count": compromised_count,
            "survival_rate": survival_rate,
            "category_breakdown": category_breakdown,
            "difficulty_mix": difficulty_mix or {},
            "cross_check_agreement_rate": cross_check_agreement_rate,
            "verdict_ids": [v.id for v in verdicts]
        }
        report_hash = compute_sha256(report_payload)

        report = RedTeamReport(
            report_id=f"rep-redteam-{uuid.uuid4().hex[:8]}",
            blueprint_id=blueprint.blueprint_id,
            tenant_id=blueprint.tenant_id,
            total_attacks=total_attacks,
            blocked_count=blocked_count,
            degraded_count=degraded_count,
            compromised_count=compromised_count,
            survival_rate=survival_rate,
            category_breakdown=category_breakdown,
            difficulty_mix=difficulty_mix or {},
            attack_verdicts=verdicts,
            cross_check_agreement_rate=cross_check_agreement_rate,
            report_hash=report_hash
        )
        return report

    async def run_full_redteam_campaign(
        self,
        blueprint: AgentBlueprint,
        attacks_per_persona: int = 3,
        generator_model: str = "gpt-4o",
        include_ollama: bool = True,
        concurrency: int = 10,
        cross_check_sample_rate: float = 0.20
    ) -> RedTeamReport:
        """
        Runs the end-to-end Red Team pipeline:
        Generate -> Quality Gate -> Concurrent Multi-turn Attack -> Impartial Judge -> Cross Check -> Assemble Report -> Persist.
        """
        raw_attacks = await self.generate_full_campaign(
            blueprint=blueprint,
            attacks_per_persona=attacks_per_persona,
            model=generator_model,
            include_ollama=include_ollama
        )
        gate_res = self.apply_quality_gate(blueprint, raw_attacks)
        passed_attacks = gate_res.passed_attacks

        transcripts = await self.execute_attack_batch_concurrently(
            blueprint=blueprint,
            attacks=passed_attacks,
            concurrency=concurrency
        )

        verdicts = await self.judge_transcripts_batch(
            blueprint=blueprint,
            transcripts=transcripts,
            generator_model=generator_model,
            concurrency=concurrency
        )

        enriched_verdicts, agreement_rate = await self.perform_judge_cross_check(
            blueprint=blueprint,
            transcripts=transcripts,
            verdicts=verdicts,
            sample_rate=cross_check_sample_rate
        )

        report = self.assemble_redteam_report(
            blueprint=blueprint,
            verdicts=enriched_verdicts,
            difficulty_mix=gate_res.difficulty_counts,
            cross_check_agreement_rate=agreement_rate
        )
        await self.repo.save_redteam_report(report)
        return report

    async def stream_full_redteam_campaign(
        self,
        blueprint: AgentBlueprint,
        attacks_per_persona: int = 3,
        generator_model: str = "gpt-4o",
        include_ollama: bool = True,
        concurrency: int = 10,
        cross_check_sample_rate: float = 0.20
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams live Red Team campaign events in real time as each attack is executed and judged.
        """
        yield {
            "type": "status",
            "stage": "generating",
            "message": "Generating adversarial attack vectors across diverse attacker personas..."
        }

        raw_attacks = await self.generate_full_campaign(
            blueprint=blueprint,
            attacks_per_persona=attacks_per_persona,
            model=generator_model,
            include_ollama=include_ollama
        )

        yield {
            "type": "status",
            "stage": "quality_gating",
            "message": "Applying attack quality gate: verifying target surfaces and eliminating duplicates..."
        }

        gate_res = self.apply_quality_gate(blueprint, raw_attacks)
        passed_attacks = gate_res.passed_attacks

        yield {
            "type": "campaign_init",
            "total_attacks": len(passed_attacks),
            "difficulty_mix": gate_res.difficulty_counts,
            "rejected_off_target": len(gate_res.rejected_off_target),
            "rejected_duplicates": len(gate_res.rejected_duplicates)
        }

        yield {
            "type": "status",
            "stage": "attacking",
            "message": f"Executing {len(passed_attacks)} attacks concurrently and streaming live verdicts..."
        }

        transcripts: List[ExecutedAttackTranscript] = []
        verdicts: List[AttackVerdict] = []
        completed_count = 0

        # Stream attack execution and immediately judge each one
        async for _, transcript in self.stream_attack_execution(
            blueprint=blueprint,
            attacks=passed_attacks,
            concurrency=concurrency
        ):
            transcripts.append(transcript)
            verdict = await self.judge_attack_transcript(
                blueprint=blueprint,
                transcript=transcript,
                generator_model=generator_model
            )
            verdicts.append(verdict)
            completed_count += 1

            yield {
                "type": "verdict",
                "completed": completed_count,
                "total": len(passed_attacks),
                "verdict": verdict.model_dump(mode="json")
            }

        yield {
            "type": "status",
            "stage": "cross_checking",
            "message": "Selecting 20% sample for independent judge cross-checking..."
        }

        enriched_verdicts, agreement_rate = await self.perform_judge_cross_check(
            blueprint=blueprint,
            transcripts=transcripts,
            verdicts=verdicts,
            sample_rate=cross_check_sample_rate
        )

        yield {
            "type": "cross_check_complete",
            "agreement_rate": agreement_rate
        }

        report = self.assemble_redteam_report(
            blueprint=blueprint,
            verdicts=enriched_verdicts,
            difficulty_mix=gate_res.difficulty_counts,
            cross_check_agreement_rate=agreement_rate
        )
        await self.repo.save_redteam_report(report)

        yield {
            "type": "report_ready",
            "report": report.model_dump(mode="json")
        }


