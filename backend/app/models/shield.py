import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PolicyObject(BaseModel):
    policy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    spec_id: str
    rate_limits: Dict[str, Any] = Field(default_factory=dict)
    topic_boundaries: Dict[str, List[str]] = Field(default_factory=dict)
    escalation_rules: List[Dict[str, Any]] = Field(default_factory=list)
    domain_disclaimers: List[str] = Field(default_factory=list)
    audit_spec: Dict[str, Any] = Field(default_factory=dict)
    builder_policy_compliance: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
