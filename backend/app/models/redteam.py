import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AttackPromptTurn(BaseModel):
    turn: int = 1
    prompt: str
    intended_violation: str

class AttackerPersonaOutput(BaseModel):
    persona: str
    attack_vector: str
    difficulty: str = "moderate"
    attack_prompts: List[AttackPromptTurn] = Field(default_factory=list)

class GeneratedAttackTurn(BaseModel):
    turn: int = 1
    prompt: str
    expected_behavior: str
    intended_violation: str

class GeneratedAttackCase(BaseModel):
    attack_id: str = Field(default_factory=lambda: f"ATK-{uuid.uuid4().hex[:6].upper()}")
    attacker_persona: str
    category: str  # "injection", "extraction", "tool_abuse", "social_engineering", "multilingual"
    attack_vector: str
    target_surface: str = "boundaries"  # "system_prompt", "tools", "guardrails", "boundaries"
    target_element: str = ""
    difficulty: str = "moderate"  # "trivial", "moderate", "hard"
    is_multi_turn: bool = False
    turns: List[GeneratedAttackTurn] = Field(default_factory=list)

class GeneratedAttacksBatch(BaseModel):
    attacks: List[GeneratedAttackCase] = Field(default_factory=list)


class AttackVerdict(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # "injection", "hijack", "extraction", "boundary", "multilingual"
    attacker_persona: str
    attacker_model: str
    prompt: str
    response: str
    verdict: str  # "BLOCKED", "DEGRADED", "COMPROMISED"
    cited_evidence: str
    judge_model: str

class RedTeamReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id: str
    tenant_id: str = "tenant-default"
    total_attacks: int
    blocked_count: int
    degraded_count: int
    compromised_count: int
    survival_rate: float
    category_breakdown: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    difficulty_mix: Dict[str, int] = Field(default_factory=dict)
    attack_verdicts: List[AttackVerdict] = Field(default_factory=list)
    cross_check_agreement_rate: Optional[float] = None
    report_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
