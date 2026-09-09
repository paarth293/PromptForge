import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class RateLimitConfig(BaseModel):
    requests_per_minute: int = 60
    tokens_per_day: int = 500000
    burst_limit: int = 10


class TopicBoundaries(BaseModel):
    whitelisted_topics: List[str] = Field(default_factory=list)
    blocked_topics: List[str] = Field(default_factory=list)


class EscalationRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"ESC-{uuid.uuid4().hex[:6].upper()}")
    trigger: str
    condition: str
    target_queue: str = "human_supervisor"
    required_context_fields: List[str] = Field(default_factory=list)


class AuditLoggingSpec(BaseModel):
    logged_events: List[str] = Field(
        default_factory=lambda: [
            "user_turn",
            "agent_reply",
            "tool_call",
            "guardrail_trigger",
            "policy_block",
            "escalation_event",
        ]
    )
    retention_days: int = 90
    pii_masking_enabled: bool = True
    access_tier: str = "compliance_and_ops"


class FallbackBehavior(BaseModel):
    on_rate_limit: str = "You have reached the temporary rate limit. Please try again shortly."
    on_ambiguity: str = "Could you please clarify your request? I want to make sure I assist you accurately."
    on_guardrail_block: str = "I cannot fulfill this request as it conflicts with our safety and operational policy."
    on_system_error: str = "A temporary system issue occurred. Our support engineers have been notified."


class DomainRiskAssessment(BaseModel):
    detected_domain: str = "general"
    risk_level: str = "low"  # "low", "medium", "high", "critical"
    auto_detected: bool = True
    mandatory_disclaimers: List[str] = Field(default_factory=list)


class BuilderPolicyEvaluation(BaseModel):
    impersonation_detected: bool = False
    impersonated_entity: Optional[str] = None
    high_risk_capabilities: List[str] = Field(default_factory=list)
    review_required: bool = False
    refusal_guidance: Optional[str] = None


class PolicyObject(BaseModel):
    policy_id: str = Field(default_factory=lambda: f"pol-{uuid.uuid4().hex[:8]}")
    spec_id: str = ""
    blueprint_id: Optional[str] = None
    domain: str = "general"
    domain_risk: DomainRiskAssessment = Field(
        default_factory=lambda: DomainRiskAssessment(
            detected_domain="general",
            risk_level="low",
            auto_detected=True,
            mandatory_disclaimers=[],
        )
    )
    domain_disclaimers: List[str] = Field(default_factory=list)
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)
    topic_boundaries: TopicBoundaries = Field(default_factory=TopicBoundaries)
    escalation_rules: List[EscalationRule] = Field(default_factory=list)
    audit_spec: AuditLoggingSpec = Field(default_factory=AuditLoggingSpec)
    fallback_behavior: FallbackBehavior = Field(default_factory=FallbackBehavior)
    builder_policy: BuilderPolicyEvaluation = Field(default_factory=BuilderPolicyEvaluation)
    builder_policy_compliance: bool = True
    policy_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
