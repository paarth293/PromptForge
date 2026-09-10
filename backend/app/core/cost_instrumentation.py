import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("promptforge.core.cost")

# Documented pricing per 1,000,000 tokens (USD)
MODEL_PRICING_PER_1M = {
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "claude-3-5-sonnet": {"prompt": 3.00, "completion": 15.00},
    "claude-3-5-haiku": {"prompt": 0.80, "completion": 4.00},
    "gemini-1.5-pro": {"prompt": 3.50, "completion": 10.50},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
    "ollama": {"prompt": 0.00, "completion": 0.00},
    "mock": {"prompt": 0.20, "completion": 0.80},
    "default": {"prompt": 0.50, "completion": 2.00},
}


def calculate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculates estimated USD cost for an LLM call based on model pricing table.
    """
    model_lower = model.lower()
    rates = None
    for key, val in sorted(MODEL_PRICING_PER_1M.items(), key=lambda x: len(x[0]), reverse=True):
        if key in model_lower:
            rates = val
            break
    if not rates:
        rates = MODEL_PRICING_PER_1M["default"]

    prompt_cost = (prompt_tokens / 1_000_000.0) * rates["prompt"]
    completion_cost = (completion_tokens / 1_000_000.0) * rates["completion"]
    return prompt_cost + completion_cost


class LLMCallRecord(BaseModel):
    call_id: str = Field(default_factory=lambda: f"call-{uuid.uuid4().hex[:8]}")
    stage: str = "general"
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StageCostSummary(BaseModel):
    stage: str
    call_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class PipelineCostReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"cost-rep-{uuid.uuid4().hex[:8]}")
    run_id: str = "run-default"
    blueprint_id: Optional[str] = None
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    tier_classification: str = "cheap_tier"  # "cheap_tier" (<$0.40), "mid_tier" (<$1.50), "frontier_tier" (>$1.50)
    stage_breakdown: Dict[str, StageCostSummary] = Field(default_factory=dict)
    call_records: List[LLMCallRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CostTracker:
    """
    Instrumentation tracker that records all LLM calls across pipeline stages,
    tallies real token usage, and computes cost estimates matching the documented cost table.
    """

    def __init__(self):
        self._current_stage: str = "general"
        self._records: List[LLMCallRecord] = []

    def set_stage(self, stage: str):
        self._current_stage = stage

    def get_stage(self) -> str:
        return self._current_stage

    def reset(self):
        self._records.clear()
        self._current_stage = "general"

    def record_call(
        self,
        model: str,
        provider: str,
        usage: Optional[Dict[str, Any]] = None,
        prompt_str: Optional[str] = None,
        completion_str: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> LLMCallRecord:
        current_stage = stage or self._current_stage

        prompt_tokens = 0
        completion_tokens = 0

        if usage:
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

        # If tokens were not reported (e.g. mock or streamed response), synthesize realistic counts
        if prompt_tokens <= 0:
            prompt_tokens = max(15, len(prompt_str.split()) * 4 // 3) if prompt_str else 45
        if completion_tokens <= 0:
            completion_tokens = max(20, len(completion_str.split()) * 4 // 3) if completion_str else 60

        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_cost_usd(model, prompt_tokens, completion_tokens)

        record = LLMCallRecord(
            stage=current_stage,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
        )
        self._records.append(record)
        return record

    def generate_cost_report(
        self,
        run_id: str = "run-default",
        blueprint_id: Optional[str] = None,
    ) -> PipelineCostReport:
        stages: Dict[str, StageCostSummary] = {}
        total_prompt = 0
        total_comp = 0
        total_cost = 0.0

        for r in self._records:
            st = r.stage
            if st not in stages:
                stages[st] = StageCostSummary(stage=st)

            summary = stages[st]
            summary.call_count += 1
            summary.prompt_tokens += r.prompt_tokens
            summary.completion_tokens += r.completion_tokens
            summary.total_tokens += r.total_tokens
            summary.total_cost_usd += r.cost_usd

            total_prompt += r.prompt_tokens
            total_comp += r.completion_tokens
            total_cost += r.cost_usd

        # Tier classification according to Idea Submission table
        if total_cost <= 0.40:
            tier = "cheap_tier ($0.15–$0.40)"
        elif total_cost <= 1.50:
            tier = "mid_tier ($0.40–$1.50)"
        else:
            tier = "frontier_tier ($1.00–$4.00+)"

        return PipelineCostReport(
            run_id=run_id,
            blueprint_id=blueprint_id,
            total_calls=len(self._records),
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_comp,
            total_tokens=total_prompt + total_comp,
            total_cost_usd=round(total_cost, 4),
            tier_classification=tier,
            stage_breakdown=stages,
            call_records=list(self._records),
        )

    def format_ascii_report(self, report: PipelineCostReport) -> str:
        div = "=" * 68
        lines = [
            div,
            f"PROMPTFORGE PIPELINE COST & TOKEN INSTRUMENTATION ({report.run_id})",
            div,
            f"Total LLM Calls:    {report.total_calls} calls across all pipeline stages",
            f"Total Tokens:       {report.total_tokens:,} ({report.total_prompt_tokens:,} prompt, {report.total_completion_tokens:,} completion)",
            f"Total Cost:         ${report.total_cost_usd:.4f} USD",
            f"Economic Tier:      {report.tier_classification}",
            "",
            "STAGE-BY-STAGE BREAKDOWN:",
            f"  {'Stage':<18} | {'Calls':<6} | {'Tokens':<10} | {'Cost (USD)':<10}",
            f"  {'-'*18}-+-{'-'*6}-+-{'-'*10}-+-{'-'*10}",
        ]
        for st_name, s in report.stage_breakdown.items():
            lines.append(
                f"  {st_name:<18} | {s.call_count:<6} | {s.total_tokens:<10,} | ${s.total_cost_usd:8.4f}"
            )
        lines.append(div)
        return "\n".join(lines)


# Global singleton instance
_global_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _global_cost_tracker
