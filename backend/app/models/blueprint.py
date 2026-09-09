import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .harden import PatchEntry


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    endpoint_binding: Optional[str] = None
    is_simulated: bool = False
    high_risk: bool = False
    high_risk_category: Optional[str] = None

class Guardrail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    layer: str = "semantic"  # "middleware" or "semantic"
    pattern_or_rule: str
    action: str = "block"  # "block", "redact", "escalate"
    probes_passed: bool = True

class FewShotMessage(BaseModel):
    role: str
    content: str

class FewShotConversation(BaseModel):
    scenario_type: str  # "happy_path", "edge_case", "adversarial_block", "tool_use", "escalation"
    messages: List[FewShotMessage]

class ProvenanceRegistryEntry(BaseModel):
    registry_id: str = Field(default_factory=lambda: f"REG-{uuid.uuid4().hex[:8].upper()}")
    agent_id: str
    blueprint_id: str
    forger_id: str
    agent_name: str
    watermark: str
    system_prompt_marker: str
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance_hash: Optional[str] = None

class AgentBlueprint(BaseModel):
    blueprint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    spec_id: str
    tenant_id: str = "tenant-default"
    version: int = 1
    parent_blueprint_id: Optional[str] = None
    agent_name: str
    system_prompt: str
    tools: List[ToolSchema] = Field(default_factory=list)
    guardrails: List[Guardrail] = Field(default_factory=list)
    few_shot_examples: List[FewShotConversation] = Field(default_factory=list)
    applied_patches: List[PatchEntry] = Field(default_factory=list)
    provenance_watermark: str = "built-with-promptforge-v1"
    provenance_record: Optional[ProvenanceRegistryEntry] = None
    review_required: bool = False
    review_flags: List[str] = Field(default_factory=list)
    blueprint_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

