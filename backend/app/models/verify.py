import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from pydantic import BaseModel, Field


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
