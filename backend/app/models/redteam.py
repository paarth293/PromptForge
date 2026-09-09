import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    seed_source: str = "seed_corpus"  # "seed_corpus" or "live_playbook"
    turns: List[GeneratedAttackTurn] = Field(default_factory=list)

class GeneratedAttacksBatch(BaseModel):
    attacks: List[GeneratedAttackCase] = Field(default_factory=list)

class AttackTurnRecord(BaseModel):
    turn_index: int
    user_prompt: str
    agent_response: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    blocked: bool = False
    guardrail_triggered: Optional[str] = None

class ExecutedAttackTranscript(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_id: str
    blueprint_id: str
    attacker_persona: str
    category: str
    attack_vector: str
    target_surface: str = "boundaries"
    target_element: str = ""
    difficulty: str = "moderate"
    is_multi_turn: bool = False
    failure_mode: str = "direct_probe"
    seed_source: str = "seed_corpus"
    turns: List[AttackTurnRecord] = Field(default_factory=list)
    final_response: str = ""
    was_blocked_any_turn: bool = False
    guardrail_triggered: Optional[str] = None



class AttackJudgmentOutput(BaseModel):
    verdict: str  # "BLOCKED", "DEGRADED", "COMPROMISED"
    verdict_rationale: str
    cited_evidence: List[str] = Field(default_factory=list)
    violation_detected: bool = False
    violated_boundary_or_policy: Optional[str] = None
    severity_score: float = 0.0


class AttackVerdict(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_id: Optional[str] = None
    session_id: Optional[str] = None
    category: str  # "injection", "hijack", "extraction", "boundary", "multilingual"
    attacker_persona: str
    attacker_model: str
    prompt: str
    response: str
    verdict: str  # "BLOCKED", "DEGRADED", "COMPROMISED"
    verdict_rationale: str = ""
    cited_evidence: str = ""
    violation_detected: bool = False
    violated_boundary_or_policy: Optional[str] = None
    severity_score: float = 0.0
    judge_model: str
    seed_source: str = "seed_corpus"
    cross_check_model: Optional[str] = None
    cross_check_verdict: Optional[str] = None
    cross_check_agrees: Optional[bool] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
