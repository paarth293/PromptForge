import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class Chain10EvaluationOutput(BaseModel):
    case_id: str
    passed: bool
    match_method: str = "factual_alignment"
    reasoning: str = ""
    key_discrepancies: List[str] = Field(default_factory=list)


class GroundTruthCaseResult(BaseModel):
    case_id: str
    question: str
    expected_answer: str
    actual_response: str
    source: str = "generated"  # "user" or "generated"
    category: str = "general"
    passed: bool
    match_method: str  # "exact_match", "regex_match", "deterministic_boundary", "policy_refusal", "factual_alignment"
    reasoning: Optional[str] = None
    key_discrepancies: List[str] = Field(default_factory=list)


class GroundTruthEvaluationResult(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id: str
    user_gold_score: Optional[Tuple[int, int]] = None  # (passed, total)
    generated_set_score: Tuple[int, int] = (0, 0)      # (passed, total)
    total_cases: int = 0
    total_passed: int = 0
    user_gold_raw: Optional[str] = None   # e.g. "4/4"
    generated_set_raw: str = "0/0"        # e.g. "7/8"
    user_weight: float = 0.70             # User-supplied gold weighted highest
    generated_weight: float = 0.30
    weighted_accuracy: float = 1.0        # Computed with disclosed formula
    disclosed_split: str = ""             # e.g. "User Gold: 4 cases (weight 70%), Generated Set: 8 cases (weight 30%)"
    case_results: List[GroundTruthCaseResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsistencyRunOutput(BaseModel):
    run_index: int
    response_text: str
    tool_call_sequence: List[str] = Field(default_factory=list)
    extracted_facts: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)


class ConsistencyEvaluationResult(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id: str
    task_prompt: str
    total_runs: int = 5
    consistent_runs: int = 5
    consistency_score: Tuple[int, int] = (5, 5)  # (matched, runs)
    consistency_raw: str = "5/5"
    tool_sequence_consistent: bool = True
    average_factual_similarity: float = 1.0
    is_consistent: bool = True
    runs: List[ConsistencyRunOutput] = Field(default_factory=list)
    discrepancy_reasons: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))



class VerificationScorecard(BaseModel):
    scorecard_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id: str
    user_gold_score: Optional[Tuple[int, int]] = None  # (passed, total)
    generated_set_score: Tuple[int, int]  # (passed, total)
    goal_completion_score: Tuple[int, int]  # (passed, total)
    consistency_score: Tuple[int, int]  # (matched, runs)
    adversarial_survival_score: Tuple[int, int]  # (blocked, total)
    judge_cross_check: Optional[Tuple[int, int]] = None  # (agreed, sampled)
    alignment_audit_score: float = 1.0  # 0.0 to 1.0
    promptforge_composite_score: int  # 0 to 100
    formula_disclosed: str
    scorecard_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

