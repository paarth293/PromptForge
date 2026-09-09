import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = "tenant-default"
    agent_id: str
    event_type: str
    event_payload: Dict[str, Any] = Field(default_factory=dict)
    prev_event_hash: str = "GENESIS"
    event_hash: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def prev_hash(self) -> str:
        return self.prev_event_hash
