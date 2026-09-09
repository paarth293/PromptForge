import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Capability(BaseModel):
    name: str
    description: str
    confirmed: bool = True

class AgentSpec(BaseModel):
    spec_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = "tenant-default"
    raw_description: str
    agent_name: str = "Assistant"
    domain: str = "general"
    inferred_capabilities: List[Capability] = Field(default_factory=list)
    boundaries: List[str] = Field(default_factory=list)
    risk_domain: Optional[str] = None
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)
    confirmed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
