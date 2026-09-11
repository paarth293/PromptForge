import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DeploymentPackage(BaseModel):
    deployment_id: str = Field(default_factory=lambda: f"DEP-{uuid.uuid4().hex[:10].upper()}")
    agent_id: str
    blueprint_id: str
    tenant_id: str = "tenant-default"
    agent_name: str
    version: int = 1
    status: str = "active"  # "active", "suspended", "retired"
    shareable_url: str
    chat_api_url: str
    public_verification_url: str
    certificate_id: Optional[str] = None
    composite_fingerprint: Optional[str] = None
    system_prompt_preview: str = ""
    tools_count: int = 0
    guardrails_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    share_token: Optional[str] = None
    deployed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
