import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AdversarialPlaybookEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_category: str  # "injection", "hijack", "extraction", "boundary", "multilingual", "seam"
    domain: str = "general"
    anonymized_attack_pattern: str
    target_surface: str
    remediation_pattern: str
    source_agent_hash: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
