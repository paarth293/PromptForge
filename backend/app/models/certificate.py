import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BirthCertificate(BaseModel):
    certificate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    blueprint_hash: str
    red_team_report_hash: str
    scorecard_hash: str
    genesis_audit_hash: str
    latest_audit_hash: str
    composite_fingerprint: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = True
