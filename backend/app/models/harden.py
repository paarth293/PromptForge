import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class PatchEntry(BaseModel):
    patch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    target: str  # "system_prompt", "guardrails", "tool_policy"
    diff: str
    rationale: str

class HardeningLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initial_blueprint_id: str
    hardened_blueprint_id: str
    initial_survival_rate: float
    final_survival_rate: float
    pass_count: int
    applied_patches: List[PatchEntry] = Field(default_factory=list)
    log_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
