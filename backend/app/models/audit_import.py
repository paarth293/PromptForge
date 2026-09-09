from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .blueprint import ToolSchema


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
