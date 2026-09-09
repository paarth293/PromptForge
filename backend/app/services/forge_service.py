import logging
from typing import Optional

from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.spec import AgentSpec

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
