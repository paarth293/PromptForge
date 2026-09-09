import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

from .blueprint import AgentBlueprint

PROMPT_STRATEGIES: List[str] = [
    "boundary_first",
    "role_imperative",
    "step_by_step_reasoning",
    "conversational_empathetic",
    "concise_direct",
    "adversarial_hardened",
    "domain_expert",
    "policy_explicit",
]


class EvolveCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"CAND-{uuid.uuid4().hex[:8].upper()}")
    spec_id: str
    blueprint_id: str
    generation: int = 0
    strategy: str = "role_imperative"
    system_prompt: str
    fitness_score: Optional[float] = None
    survival_rate: Optional[float] = None
    goal_completion_rate: Optional[float] = None
    consistency_score: Optional[float] = None
    parent_ids: List[str] = Field(default_factory=list)
    mutation_type: Optional[str] = None  # "initial_population", "crossover", "mutation_patch"
    mutation_details: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvolveGenerationRecord(BaseModel):
    generation: int
    candidates: List[EvolveCandidate] = Field(default_factory=list)
    best_candidate_id: Optional[str] = None
    best_fitness: Optional[float] = None
    average_fitness: Optional[float] = None


class EvolveLineageLog(BaseModel):
    lineage_id: str = Field(default_factory=lambda: f"LIN-{uuid.uuid4().hex[:8].upper()}")
    tenant_id: str = "tenant-default"
    spec_id: str
    domain: str = "general"
    generations: List[EvolveGenerationRecord] = Field(default_factory=list)
    champion_candidate: Optional[EvolveCandidate] = None
    champion_blueprint_id: Optional[str] = None
    total_candidates_evaluated: int = 0
    is_cached_demo_run: bool = False
    execution_time_seconds: float = 0.0
    log_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PopulationGeneratorResult(BaseModel):
    spec_id: str
    population_size: int
    candidates: List[EvolveCandidate] = Field(default_factory=list)
    blueprints: List[AgentBlueprint] = Field(default_factory=list)


class DeepForgeRunRequest(BaseModel):
    spec_id: str
    population_size: int = 6
    generations_count: int = 2
    attacks_per_candidate: int = 4
    is_background: bool = True
    cached_demo_preferred: bool = True


class CrossoverRecombinationOutput(BaseModel):
    offspring_system_prompt: str
    word_count: int
    inherited_from_parent_a: List[str] = Field(default_factory=list)
    inherited_from_parent_b: List[str] = Field(default_factory=list)
    recombination_rationale: str = ""

