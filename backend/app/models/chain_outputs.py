from typing import Any, Dict, List

from pydantic import BaseModel, Field


class SystemPromptOutput(BaseModel):
    system_prompt: str
    word_count: int
    framework_sections: Dict[str, str] = Field(default_factory=dict)

class ToolSchemaOutput(BaseModel):
    tools: List[Dict[str, Any]] = Field(default_factory=list)

class GuardrailItem(BaseModel):
    name: str
    layer: str  # "middleware" or "semantic"
    pattern_or_rule: str
    action: str = "block"
    probes_passed: bool = True

class GuardrailsOutput(BaseModel):
    guardrails: List[GuardrailItem] = Field(default_factory=list)

class FewShotExampleItem(BaseModel):
    scenario_type: str
    messages: List[Dict[str, str]]

class FewShotExamplesOutput(BaseModel):
    examples: List[FewShotExampleItem] = Field(default_factory=list)
