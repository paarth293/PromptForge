import logging
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..models.shield import PolicyObject

logger = logging.getLogger("promptforge.core.policy_middleware")


class PolicyMiddlewareResult(BaseModel):
    allowed: bool = True
    action: str = "allow"  # "allow", "block", "escalate"
    blocked_reason: Optional[str] = None
    policy_rule: Optional[str] = None
    response_override: Optional[str] = None
    escalation_queue: Optional[str] = None
    context_data: Dict[str, Any] = Field(default_factory=dict)


class PolicyEnforcementMiddleware:
    """
    Deterministic Policy Enforcement Middleware.
    Enforces non-negotiable policy constraints in code OUTSIDE the LLM prompt context:
    1. Rate Limits (requests per minute, burst limit)
    2. Topic Blocklist (blocked topics / prohibited content domains)
    3. Tool Policy Rules (parameter ceilings e.g. 'refund > $500 requires approval')
    """

    def __init__(self):
        # In-memory sliding window: client_id -> list of float timestamps
        self._rate_limit_windows: Dict[str, List[float]] = defaultdict(list)

    def reset(self):
        """Clears in-memory rate limit windows."""
        self._rate_limit_windows.clear()

    def check_rate_limit(
        self,
        policy: PolicyObject,
        client_id: str,
        now: Optional[float] = None
    ) -> PolicyMiddlewareResult:
        """
        Enforces deterministic sliding window rate limiting.
        """
        current_time = now if now is not None else time.time()
        window = self._rate_limit_windows[client_id]

        # Evict timestamps older than 60 seconds
        cutoff = current_time - 60.0
        self._rate_limit_windows[client_id] = [t for t in window if t > cutoff]
        recent_timestamps = self._rate_limit_windows[client_id]

        rpm_limit = policy.rate_limits.requests_per_minute
        burst_limit = policy.rate_limits.burst_limit

        # Check burst limit (requests within last 2 seconds)
        burst_cutoff = current_time - 2.0
        burst_count = sum(1 for t in recent_timestamps if t > burst_cutoff)

        if burst_count >= burst_limit:
            logger.warning(f"Rate limit middleware: client '{client_id}' exceeded burst limit ({burst_count}/{burst_limit})")
            return PolicyMiddlewareResult(
                allowed=False,
                action="block",
                blocked_reason=f"Burst rate limit of {burst_limit} requests in 2 seconds exceeded.",
                policy_rule="rate_limit:burst_limit",
                response_override=policy.fallback_behavior.on_rate_limit
            )

        if len(recent_timestamps) >= rpm_limit:
            logger.warning(f"Rate limit middleware: client '{client_id}' exceeded RPM limit ({len(recent_timestamps)}/{rpm_limit})")
            return PolicyMiddlewareResult(
                allowed=False,
                action="block",
                blocked_reason=f"Rate limit of {rpm_limit} requests per minute exceeded.",
                policy_rule="rate_limit:rpm_limit",
                response_override=policy.fallback_behavior.on_rate_limit
            )

        # Record this request timestamp
        self._rate_limit_windows[client_id].append(current_time)
        return PolicyMiddlewareResult(allowed=True, action="allow")

    def check_topic_blocklist(
        self,
        policy: PolicyObject,
        text: str
    ) -> PolicyMiddlewareResult:
        """
        Enforces topic boundaries against blocked topics.
        """
        text_lower = text.lower()
        for blocked in policy.topic_boundaries.blocked_topics:
            blocked_clean = blocked.strip().lower()
            if not blocked_clean:
                continue

            # Check direct phrase or regex
            try:
                if re.search(rf"\b{re.escape(blocked_clean)}\b", text_lower):
                    logger.warning(f"Topic blocklist middleware: blocked topic '{blocked}' matched in input.")
                    return PolicyMiddlewareResult(
                        allowed=False,
                        action="block",
                        blocked_reason=f"Input touches strictly prohibited topic: '{blocked}'",
                        policy_rule=f"topic_blocklist:{blocked}",
                        response_override=policy.fallback_behavior.on_guardrail_block
                    )
            except re.error:
                if blocked_clean in text_lower:
                    logger.warning(f"Topic blocklist middleware: blocked substring '{blocked}' matched in input.")
                    return PolicyMiddlewareResult(
                        allowed=False,
                        action="block",
                        blocked_reason=f"Input touches strictly prohibited topic: '{blocked}'",
                        policy_rule=f"topic_blocklist:{blocked}",
                        response_override=policy.fallback_behavior.on_guardrail_block
                    )

        return PolicyMiddlewareResult(allowed=True, action="allow")

    def check_tool_policy(
        self,
        policy: PolicyObject,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> PolicyMiddlewareResult:
        """
        Deterministic Tool Policy Enforcement.
        Checks tool arguments against hard thresholds (e.g. refund amount > $500 requires approval).
        Blocks execution directly at middleware layer before invoking backend API or simulated tool.
        """
        tool_lower = tool_name.lower()

        # 1. Refund Amount Limit Rule ($500 standard policy limit)
        if "refund" in tool_lower:
            amount = parameters.get("amount")
            if amount is not None:
                try:
                    num_amount = float(amount)
                    # Check against $500 cap
                    refund_limit = 500.0
                    if num_amount > refund_limit:
                        logger.warning(
                            f"Tool policy middleware: BLOCKED {tool_name} with amount ${num_amount} > ${refund_limit}"
                        )
                        return PolicyMiddlewareResult(
                            allowed=False,
                            action="escalate",
                            blocked_reason=f"Refund amount ${num_amount:.2f} exceeds automated policy limit of ${refund_limit:.2f}. Requires human manager authorization.",
                            policy_rule="tool_policy:refund_cap_500",
                            escalation_queue="compliance_supervisor",
                            context_data={"amount": num_amount, "limit": refund_limit, "tool_name": tool_name}
                        )
                except (ValueError, TypeError):
                    pass

        # 2. Check general escalation rules in policy matching this trigger
        for rule in policy.escalation_rules:
            trigger_lower = rule.trigger.lower()
            if "dispute" in trigger_lower or "threshold" in trigger_lower or "escalat" in trigger_lower:
                amount = parameters.get("amount")
                if amount is not None:
                    try:
                        if float(amount) > 500.0:
                            return PolicyMiddlewareResult(
                                allowed=False,
                                action="escalate",
                                blocked_reason=f"Violates policy rule {rule.rule_id}: {rule.condition}",
                                policy_rule=f"escalation_rule:{rule.rule_id}",
                                escalation_queue=rule.target_queue,
                                context_data=parameters
                            )
                    except (ValueError, TypeError):
                        pass

        return PolicyMiddlewareResult(allowed=True, action="allow")


# Global singleton instance
_global_policy_middleware: Optional[PolicyEnforcementMiddleware] = None

def get_policy_middleware() -> PolicyEnforcementMiddleware:
    global _global_policy_middleware
    if _global_policy_middleware is None:
        _global_policy_middleware = PolicyEnforcementMiddleware()
    return _global_policy_middleware
