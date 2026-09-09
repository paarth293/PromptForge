import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    endpoint_binding: Optional[str] = None
    is_simulated: bool = False

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

class AgentBlueprint(BaseModel):
    blueprint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    spec_id: str
    tenant_id: str = "tenant-default"
    version: int = 1
    agent_name: str
    system_prompt: str
    tools: List[ToolSchema] = Field(default_factory=list)
    guardrails: List[Guardrail] = Field(default_factory=list)
    few_shot_examples: List[FewShotConversation] = Field(default_factory=list)
    provenance_watermark: str = "built-with-promptforge-v1"
    blueprint_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
