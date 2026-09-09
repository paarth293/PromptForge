import json
import logging
from typing import List, Optional

from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.redteam import GeneratedAttackCase, GeneratedAttacksBatch
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
        seed_service: Optional[SeedCorpusService] = None
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.registry = get_prompt_registry()
        self.seed_service = seed_service or get_seed_corpus_service()

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
