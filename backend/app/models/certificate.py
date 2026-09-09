import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BirthCertificate(BaseModel):
    certificate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = "tenant-default"
    agent_id: str
    blueprint_hash: str
    red_team_report_hash: str
    scorecard_hash: str
    genesis_audit_hash: str
    latest_audit_hash: str
    composite_fingerprint: str
    agent_name: str = ""
    spec_id: Optional[str] = None
    composite_score: Optional[int] = None
    survival_rate: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = True


class CertificateVerificationResult(BaseModel):
    certificate_id: str
    agent_id: str
    is_valid: bool
    blueprint_integrity: bool
    redteam_report_integrity: bool
    scorecard_integrity: bool
    audit_chain_integrity: bool
    composite_fingerprint_valid: bool
    tampered_fields: List[str] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)
    audit_blocks_checked: int = 0
    composite_fingerprint: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

