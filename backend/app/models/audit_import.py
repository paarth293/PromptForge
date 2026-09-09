from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .blueprint import AgentBlueprint, ToolSchema
from .certificate import BirthCertificate
from .harden import HardeningLog
from .redteam import RedTeamReport
from .shield import PolicyObject
from .verify import VerificationScorecard


class RawPromptImportRequest(BaseModel):
    prompt: str
    agent_name: str = "Imported Prompt Agent"
    domain: str = "general"
    tools: List[ToolSchema] = Field(default_factory=list)
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)


class OpenAIAssistantImportRequest(BaseModel):
    config: Dict[str, Any]
    agent_name: Optional[str] = None
    domain: Optional[str] = "general"
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)


class BedrockAgentImportRequest(BaseModel):
    config: Dict[str, Any]
    agent_name: Optional[str] = None
    domain: Optional[str] = "general"
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)


class UniversalAuditImportRequest(BaseModel):
    format_type: str  # "raw", "openai", "bedrock"
    payload: Dict[str, Any]
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)


class AuditPipelineRunRequest(BaseModel):
    attacks_per_persona: int = 1
    survival_threshold: float = 0.80
    max_harden_passes: int = 1
    reattack_count_per_category: int = 2
    user_gold_qa: Optional[List[Dict[str, str]]] = None


class AuditImportAndRunRequest(BaseModel):
    format_type: str = "raw"  # "raw", "openai", "bedrock"
    payload: Dict[str, Any]
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)
    attacks_per_persona: int = 1
    survival_threshold: float = 0.80
    max_harden_passes: int = 1
    reattack_count_per_category: int = 2



class AuditPipelineResult(BaseModel):
    agent_id: str
    spec_id: str
    tenant_id: str
    initial_blueprint: AgentBlueprint
    active_blueprint: AgentBlueprint
    redteam_report: RedTeamReport
    hardening_log: Optional[HardeningLog] = None
    scorecard: VerificationScorecard
    policy: PolicyObject
    birth_certificate: BirthCertificate
    forge_chains_called: int = 0
    audit_events_count: int = 0
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

