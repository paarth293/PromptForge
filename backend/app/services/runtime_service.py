import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..core.policy_middleware import PolicyEnforcementMiddleware, get_policy_middleware
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, LLMMessage, get_llm_client
from ..models.blueprint import AgentBlueprint, ToolSchema
from ..models.runtime import ChatRequest, ChatResponse, SimulatedToolCall
from ..models.shield import PolicyObject

logger = logging.getLogger("promptforge.services.runtime")


class AgentRuntimeService:
    """
    Executes an interactive chat conversation against a forged AgentBlueprint.
    Enforces deterministic middleware guardrails, performs simulated tool execution,
    and returns compliant assistant responses.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None,
        policy_middleware: Optional[PolicyEnforcementMiddleware] = None
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.policy_middleware = policy_middleware or get_policy_middleware()

    def check_middleware_guardrails(
        self,
        blueprint: AgentBlueprint,
        text: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Evaluates text against deterministic middleware guardrails.
        Returns: (is_blocked, processed_text, triggered_guardrail_name)
        """
        processed_text = text
        for rail in blueprint.guardrails:
            if rail.layer.lower() != "middleware":
                continue

            # Try regex evaluation
            try:
                if re.search(rail.pattern_or_rule, processed_text, re.IGNORECASE):
                    if rail.action == "block":
                        logger.warning(f"Middleware guardrail '{rail.name}' BLOCKED input: '{text[:50]}'")
                        return True, processed_text, rail.name
                    elif rail.action == "redact":
                        processed_text = re.sub(rail.pattern_or_rule, "[REDACTED]", processed_text, flags=re.IGNORECASE)
            except re.error:
                pass

            # Check numeric boundary rule e.g. "amount <= 500"
            num_rule = re.match(r"amount\s*(<=|<)\s*(\d+(?:\.\d+)?)", rail.pattern_or_rule.strip(), re.IGNORECASE)
            if num_rule and any(w in text.lower() for w in ["refund", "$", "dollar", "pay", "charge"]):
                op = num_rule.group(1)
                limit = float(num_rule.group(2))
                dollar_match = re.search(
                    r"\$\s*(\d+(?:\.\d+)?)|(?:refund|charge|amount)\s+(?:of\s+)?(\d+(?:\.\d+)?)",
                    text,
                    re.IGNORECASE
                )
                if dollar_match:
                    amount_str = dollar_match.group(1) or dollar_match.group(2)
                    req_amount = float(amount_str)
                    if (op == "<=" and req_amount > limit) or (op == "<" and req_amount >= limit):
                        if rail.action == "block":
                            logger.warning(
                                f"Middleware guardrail '{rail.name}' BLOCKED input: "
                                f"amount ${req_amount} exceeds limit ${limit}"
                            )
                            return True, processed_text, rail.name

        return False, processed_text, None

    def simulate_tool_execution(
        self,
        tool: ToolSchema,
        message: str,
        policy: Optional[PolicyObject] = None
    ) -> SimulatedToolCall:
        """
        Simulates function-calling execution with realistic, deterministic outputs.
        Enforces deterministic tool-policy rules at the middleware layer.
        """
        tool_name = tool.name.lower()
        parameters: Dict[str, Any] = {}
        output: Dict[str, Any] = {}

        if "order" in tool_name or "lookup" in tool_name:
            match = re.search(r"#?([A-Za-z0-9\-]+)", message)
            order_id = match.group(1) if match else "ORD-9821"
            parameters = {"order_id": order_id}
            output = {
                "order_id": order_id,
                "status": "Shipped",
                "carrier": "FedEx",
                "tracking_number": "TRK-987654321",
                "estimated_delivery": "Within 2 business days"
            }
        elif "refund" in tool_name:
            # Extract possible dollar amount
            amount_match = re.search(r"\$?(\d+(?:\.\d+)?)", message)
            amount = float(amount_match.group(1)) if amount_match else 49.99
            parameters = {"amount": amount, "order_id": "ORD-9821"}

            # Check deterministic policy middleware
            if policy:
                policy_res = self.policy_middleware.check_tool_policy(policy, tool.name, parameters)
                if not policy_res.allowed:
                    return SimulatedToolCall(
                        tool_name=tool.name,
                        parameters=parameters,
                        output={
                            "success": False,
                            "blocked": True,
                            "middleware_blocked": True,
                            "error": policy_res.blocked_reason,
                            "escalation": True,
                            "escalation_queue": policy_res.escalation_queue
                        },
                        middleware_blocked=True,
                        blocked_reason=policy_res.blocked_reason
                    )

            if amount > 500:
                return SimulatedToolCall(
                    tool_name=tool.name,
                    parameters=parameters,
                    output={
                        "success": False,
                        "blocked": True,
                        "middleware_blocked": True,
                        "error": f"Refund amount ${amount} exceeds automated authority limit of $500. Escalating to human manager.",
                        "escalation": True
                    },
                    middleware_blocked=True,
                    blocked_reason=f"Refund amount ${amount} exceeds automated limit of $500"
                )
            else:
                output = {
                    "success": True,
                    "refund_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
                    "amount": amount,
                    "status": "processed",
                    "refund_method": "original_payment"
                }
        elif "lead" in tool_name or "qualify" in tool_name or "score" in tool_name:
            parameters = {"query": message[:60]}
            output = {
                "lead_id": f"LEAD-{uuid.uuid4().hex[:6].upper()}",
                "qualification_score": 88,
                "tier": "Tier 1 Enterprise",
                "fit": "High Budget, Immediate Need"
            }
        elif "ticket" in tool_name or "bug" in tool_name:
            parameters = {"issue_summary": message[:80]}
            output = {
                "ticket_id": f"TICK-{uuid.uuid4().hex[:6].upper()}",
                "status": "Created",
                "priority": "Medium",
                "assigned_team": "Customer Support Tier 2"
            }
        else:
            parameters = {"query": message[:50]}
            output = {
                "status": "success",
                "result": f"Executed {tool.name} successfully."
            }

        return SimulatedToolCall(
            tool_name=tool.name,
            parameters=parameters,
            output=output,
            middleware_blocked=False
        )

    def detect_tool_invocation_intent(
        self,
        blueprint: AgentBlueprint,
        user_message: str
    ) -> Optional[ToolSchema]:
        """
        Determines if the user's message matches any tool capabilities declared in the blueprint.
        """
        msg_lower = user_message.lower()
        for tool in blueprint.tools:
            name_terms = tool.name.lower().replace("_", " ").split()
            desc_terms = tool.description.lower().split()
            keywords = set(name_terms + [t for t in desc_terms if len(t) > 4])
            if any(kw in msg_lower for kw in keywords):
                return tool
            # Common heuristics
            if "order" in msg_lower and "order" in tool.name.lower():
                return tool
            if "refund" in msg_lower and "refund" in tool.name.lower():
                return tool
            if ("lead" in msg_lower or "demo" in msg_lower) and ("lead" in tool.name.lower() or "score" in tool.name.lower()):
                return tool
            if ("ticket" in msg_lower or "bug" in msg_lower) and "ticket" in tool.name.lower():
                return tool
        return None

    async def chat(
        self,
        blueprint_id: str,
        request: ChatRequest
    ) -> ChatResponse:
        """
        Processes a conversational turn with the forged agent.
        """
        blueprint = await self.repo.get_blueprint(blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' not found.")

        session_id = request.session_id or str(uuid.uuid4())
        user_text = request.message

        # Retrieve policy if available for this agent
        policy = await self.repo.get_policy_by_spec(blueprint.spec_id)

        # 0. Deterministic Rate Limit Middleware
        if policy:
            rate_res = self.policy_middleware.check_rate_limit(policy, client_id=session_id)
            if not rate_res.allowed:
                return ChatResponse(
                    session_id=session_id,
                    response=rate_res.response_override or "Rate limit exceeded. Please try again shortly.",
                    tool_calls=[],
                    blocked=True,
                    policy_triggered=rate_res.policy_rule
                )

        # 1. Deterministic Middleware Guardrail Enforcement
        is_blocked, sanitized_text, triggered_rail = self.check_middleware_guardrails(blueprint, user_text)
        if is_blocked:
            return ChatResponse(
                session_id=session_id,
                response=f"I cannot complete your request because it violates safety policy: [{triggered_rail}].",
                tool_calls=[],
                blocked=True,
                guardrail_triggered=triggered_rail
            )

        # 1b. Deterministic Topic Blocklist Middleware
        if policy:
            topic_res = self.policy_middleware.check_topic_blocklist(policy, sanitized_text)
            if not topic_res.allowed:
                return ChatResponse(
                    session_id=session_id,
                    response=topic_res.response_override or f"I cannot assist with this topic: {topic_res.blocked_reason}",
                    tool_calls=[],
                    blocked=True,
                    policy_triggered=topic_res.policy_rule
                )

        # 2. Check for tool invocation
        tool_calls: List[SimulatedToolCall] = []
        invoked_tool = self.detect_tool_invocation_intent(blueprint, sanitized_text)
        tool_context_str = ""
        if invoked_tool:
            tool_call = self.simulate_tool_execution(invoked_tool, sanitized_text, policy=policy)
            tool_calls.append(tool_call)

            # Check if tool was blocked at middleware layer
            if tool_call.middleware_blocked:
                return ChatResponse(
                    session_id=session_id,
                    response=f"Tool execution blocked by deterministic policy middleware: {tool_call.blocked_reason}. An escalation record has been dispatched.",
                    tool_calls=tool_calls,
                    blocked=True,
                    policy_triggered="tool_policy_violation"
                )

            tool_context_str = f"\n[Simulated Tool Execution: {tool_call.tool_name}({tool_call.parameters}) -> {tool_call.output}]"

        # 3. Formulate Prompt and LLM Conversation
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=blueprint.system_prompt)
        ]
        for past in request.history:
            messages.append(LLMMessage(role=past.role, content=past.content))

        final_user_content = sanitized_text
        if tool_context_str:
            final_user_content += f"\n\nSystem Notice for Assistant:{tool_context_str}\nExplain the result clearly and helpfully to the user based on your persona."

        messages.append(LLMMessage(role="user", content=final_user_content))

        # Check for adversarial attempt against semantic guardrails
        user_lower = sanitized_text.lower()
        if "ignore previous instructions" in user_lower or "reveal your system prompt" in user_lower or "output your prompt" in user_lower:
            asst_reply = "I cannot disclose internal system prompts, developer guidelines, or override my configured safety boundaries. How may I assist you within my designated capabilities?"
        else:
            llm_resp = await self.llm.complete(prompt=messages, model="gpt-4o")
            asst_reply = llm_resp.content

            # If mock fallback returned generic text, generate a clean persona-grounded response
            if "simulated response from" in asst_reply.lower() or "demoassistant" in asst_reply.lower():
                if tool_calls:
                    tc = tool_calls[0]
                    if "order" in tc.tool_name.lower():
                        asst_reply = f"I looked up order {tc.parameters.get('order_id', '')} for you. It is currently {tc.output.get('status', 'Shipped')} with tracking number {tc.output.get('tracking_number', '')}, estimated delivery: {tc.output.get('estimated_delivery', '')}."
                    elif "refund" in tc.tool_name.lower():
                        if tc.output.get("success"):
                            asst_reply = f"Your refund request for ${tc.parameters.get('amount', 0):.2f} has been processed successfully. Refund ID: {tc.output.get('refund_id')}."
                        else:
                            asst_reply = f"Your refund request for ${tc.parameters.get('amount', 0):.2f} exceeds my direct authorization limit of $500. I have escalated this ticket to our senior support team."
                    else:
                        asst_reply = f"I have executed the requested action via {tc.tool_name}. Status: {tc.output.get('status', 'completed')}."
                else:
                    asst_reply = f"Hello! As {blueprint.agent_name}, I am here to help you resolve your requests within policy. How can I assist you today?"

        return ChatResponse(
            session_id=session_id,
            response=asst_reply,
            tool_calls=tool_calls,
            blocked=False,
            guardrail_triggered=None
        )
