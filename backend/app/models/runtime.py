from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str

class SimulatedToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    middleware_blocked: bool = False
    blocked_reason: Optional[str] = None
    is_live_call: bool = False
    http_status: Optional[int] = None
    execution_duration_ms: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    middleware_enabled: Optional[bool] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: List[SimulatedToolCall] = Field(default_factory=list)
    blocked: bool = False
    guardrail_triggered: Optional[str] = None
    policy_triggered: Optional[str] = None
