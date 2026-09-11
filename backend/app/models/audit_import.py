from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

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
    payload: Dict[str, Any] = Field(default_factory=dict)
    user_gold_qa: List[Dict[str, str]] = Field(default_factory=list)
    attacks_per_persona: int = 1
    survival_threshold: float = 0.80
    max_harden_passes: int = 1
    reattack_count_per_category: int = 2

    # Flat alias fields for seamless client compatibility:
    agent_name: Optional[str] = None
    agent_system_prompt: Optional[str] = None
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    ingestion_format: Optional[str] = None
    target_domain: Optional[str] = None
    ground_truth_qa_set: Optional[List[Dict[str, str]]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_flat_or_nested(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Normalize format_type
        raw_fmt = data.get("ingestion_format") or data.get("format_type") or "raw"
        fmt_str = str(raw_fmt).lower().strip()
        if "bedrock" in fmt_str:
            normalized_fmt = "bedrock"
        elif "openai" in fmt_str or "gpt" in fmt_str:
            normalized_fmt = "openai"
        else:
            normalized_fmt = "raw"
        data["format_type"] = normalized_fmt

        # Normalize user_gold_qa / ground_truth_qa_set
        qa_list = data.get("user_gold_qa") or data.get("ground_truth_qa_set") or []
        if isinstance(qa_list, list):
            data["user_gold_qa"] = qa_list

        # Normalize payload
        payload = dict(data.get("payload") or {})
        prompt_val = (
            data.get("agent_system_prompt")
            or data.get("system_prompt")
            or data.get("prompt")
            or payload.get("prompt")
            or payload.get("instructions")
            or payload.get("instruction")
            or ""
        )
        agent_name_val = (
            data.get("agent_name")
            or payload.get("agent_name")
            or payload.get("name")
            or "External Support Agent"
        )
        domain_val = (
            data.get("target_domain")
            or data.get("domain")
            or payload.get("domain")
            or "customer_support"
        )

        if not payload:
            if normalized_fmt == "raw":
                payload = {
                    "prompt": prompt_val,
                    "agent_name": agent_name_val,
                    "domain": domain_val,
                    "tools": [],
                }
            elif normalized_fmt == "openai":
                payload = {
                    "name": agent_name_val,
                    "instructions": prompt_val,
                    "tools": [],
                }
            elif normalized_fmt == "bedrock":
                payload = {
                    "agentName": agent_name_val,
                    "instruction": prompt_val,
                    "actionGroups": [],
                }
        else:
            if "prompt" not in payload and prompt_val:
                payload["prompt"] = prompt_val
            if "agent_name" not in payload and agent_name_val:
                payload["agent_name"] = agent_name_val
            if "domain" not in payload and domain_val:
                payload["domain"] = domain_val

        data["payload"] = payload
        return data


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

    # Compatibility & Run metadata
    run_id: Optional[str] = None
    status: Optional[str] = "completed"
    agent_name: Optional[str] = None
    message: Optional[str] = None


class AuditStatusResponse(BaseModel):
    run_id: str
    status: str
    progress_percent: int
    message: str
    vulnerabilities_found: Optional[int] = None
    cost_so_far: Optional[float] = None


class VulnerabilityFinding(BaseModel):
    id: str
    severity: str  # "critical" | "high" | "medium" | "low"
    title: str
    description: str
    attack_payload: str
    response_received: str
    fix_recommendation: str


class AuditResultsResponse(BaseModel):
    run_id: str
    agent_name: str
    status: str
    completed_at: Optional[str]
    total_cost_usd: float
    duration_seconds: int
    vulnerabilities: List[VulnerabilityFinding]
    overall_risk_score: int  # 0-100
    summary: str



