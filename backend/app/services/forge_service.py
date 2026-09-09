import json
import logging
from typing import Optional

from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.chain_outputs import SystemPromptOutput
from ..models.spec import AgentSpec
from ..models.test_set import GeneratedTestSuite, TestCase

logger = logging.getLogger("promptforge.services.forge")

class ForgeService:
    """Orchestrates Forge lifecycle stages: Intent Decomposition, Spec Confirmation, and Blueprint Assembly."""

    def __init__(self, repo: Optional[PipelineRepository] = None, llm: Optional[LLMClient] = None):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.registry = get_prompt_registry()

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
        prompt = self.registry.render("chain_1_intent_decomposition", description=description)
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
        """
        spec_update.confirmed = True
        await self.repo.save_spec(spec_update)
        logger.info(f"Spec {spec_update.spec_id} confirmed by user.")
        return spec_update

    async def generate_test_suite(
        self,
        spec: AgentSpec,
        model: str = "claude-3-5-sonnet"
    ) -> GeneratedTestSuite:
        """
        Executes Chain 14: Synthesizes gold cases, edge cases, and incorporates user gold Q&A.
        Uses an independent model persona from the generator to prevent circular evaluation.
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
        spec_json = spec.model_dump_json(indent=2)
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
