import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..core.api_executor import ApiExecutionRequest, ApiExecutor, get_api_executor
from ..core.delimiting import delimit_tool_return, delimit_user_chat_input
from ..core.policy_middleware import PolicyEnforcementMiddleware, get_policy_middleware
from ..core.stripe_tool import StripeRefundAdapter
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
        policy_middleware: Optional[PolicyEnforcementMiddleware] = None,
        api_executor: Optional[ApiExecutor] = None,
        stripe_adapter: Optional[StripeRefundAdapter] = None,
        middleware_enabled: bool = True
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.policy_middleware = policy_middleware or get_policy_middleware()
        self.api_executor = api_executor or get_api_executor()
        self.stripe_adapter = stripe_adapter or StripeRefundAdapter(api_executor=self.api_executor)
        self.middleware_enabled = middleware_enabled

    def check_middleware_guardrails(
        self,
        blueprint: AgentBlueprint,
        text: str,
        has_policy: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Evaluates text against deterministic middleware guardrails.
        Returns: (is_blocked, processed_text, triggered_guardrail_name)
        When a Shield PolicyObject is active (has_policy=True), tool parameter ceilings (e.g. amount <= 500)
        are enforced by the dedicated PolicyEnforcementMiddleware during tool execution.
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

            # Check numeric boundary rule e.g. "amount <= 500" if no formal policy object is attached
            if not has_policy:
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
            match = re.search(r"(?:order\s*#?|#)([A-Za-z0-9\-]+)", message, re.IGNORECASE)
            if not match:
                match = re.search(r"\b(ORD-[A-Za-z0-9\-]+)\b", message, re.IGNORECASE)
            if not match:
                match = re.search(r"#?([A-Za-z0-9\-]+)", message)
            order_id = match.group(1) if match else "ORD-9821"
            parameters = {"order_id": order_id}
            output = {
                "success": True,
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

            if policy is not None and amount > 500:
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
                refund_id = f"re_test_{uuid.uuid4().hex[:16]}"
                output = {
                    "success": True,
                    "live_mode": False,
                    "stripe_refund_id": refund_id,
                    "refund_id": refund_id,
                    "amount": amount,
                    "amount_cents": int(round(amount * 100)),
                    "currency": "usd",
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

    async def execute_tool_call(
        self,
        tool: ToolSchema,
        message: str,
        policy: Optional[PolicyObject] = None
    ) -> SimulatedToolCall:
        """
        Executes a tool call. If tool.is_simulated is True, uses deterministic simulation.
        If tool.is_simulated is False and endpoint_binding is defined, invokes the real
        HTTP ApiExecutor against the allowlisted endpoint.
        Deterministic policy middleware is enforced prior to any external network dispatch.
        """
        if tool.is_simulated or not tool.endpoint_binding:
            return self.simulate_tool_execution(tool, message, policy=policy)

        tool_name = tool.name.lower()
        parameters: Dict[str, Any] = {}

        if "order" in tool_name or "lookup" in tool_name:
            match = re.search(r"(?:order\s*#?|#)([A-Za-z0-9\-]+)", message, re.IGNORECASE)
            if not match:
                match = re.search(r"\b(ORD-[A-Za-z0-9\-]+)\b", message, re.IGNORECASE)
            if not match:
                match = re.search(r"#?([A-Za-z0-9\-]+)", message)
            order_id = match.group(1) if match else "ORD-9821"
            parameters = {"order_id": order_id}
        elif "refund" in tool_name:
            amount_match = re.search(r"\$?(\d+(?:\.\d+)?)", message)
            amount = float(amount_match.group(1)) if amount_match else 49.99
            order_match = re.search(r"\b(ORD-[A-Za-z0-9\-]+)\b", message, re.IGNORECASE)
            order_id = order_match.group(1) if order_match else "ORD-9821"
            parameters = {"amount": amount, "order_id": order_id}
        else:
            parameters = {"query": message[:80]}

        # Enforce deterministic policy middleware before dispatch
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

        # Specialized Stripe test-mode refund execution
        if "refund" in tool_name and "stripe" in (tool.endpoint_binding or "").lower():
            stripe_res = await self.stripe_adapter.execute_refund(
                amount_dollars=parameters.get("amount", 49.99),
                order_id=parameters.get("order_id", "ORD-9821")
            )
            return SimulatedToolCall(
                tool_name=tool.name,
                parameters=parameters,
                output=stripe_res,
                middleware_blocked=False,
                is_live_call=True,
                http_status=200,
                execution_duration_ms=10.0
            )

        # Build URL from endpoint_binding
        url = tool.endpoint_binding
        for k, v in parameters.items():
            url = url.replace(f"{{{k}}}", str(v))

        method = "GET" if ("lookup" in tool_name or "get" in tool_name or "query" in tool_name) else "POST"
        req = ApiExecutionRequest(
            url=url,
            method=method,
            params=parameters if method == "GET" else None,
            json_body=parameters if method != "GET" else None
        )
        api_result = await self.api_executor.call_api(req)

        output_dict = (
            api_result.response_data
            if isinstance(api_result.response_data, dict)
            else {"result": api_result.response_data}
        )
        if not api_result.success:
            output_dict["success"] = False
            output_dict["error"] = api_result.error

        return SimulatedToolCall(
            tool_name=tool.name,
            parameters=parameters,
            output=output_dict,
            middleware_blocked=False,
            is_live_call=True,
            http_status=api_result.status_code,
            execution_duration_ms=api_result.execution_duration_ms
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

        # Prioritize specific action intents first (e.g. 'refund' takes precedence over 'order')
        if "refund" in msg_lower:
            for tool in blueprint.tools:
                if "refund" in tool.name.lower():
                    return tool
        if "order" in msg_lower:
            for tool in blueprint.tools:
                if "order" in tool.name.lower():
                    return tool
        if "lead" in msg_lower or "demo" in msg_lower:
            for tool in blueprint.tools:
                if "lead" in tool.name.lower() or "score" in tool.name.lower():
                    return tool
        if "ticket" in msg_lower or "bug" in msg_lower:
            for tool in blueprint.tools:
                if "ticket" in tool.name.lower():
                    return tool

        for tool in blueprint.tools:
            name_terms = tool.name.lower().replace("_", " ").split()
            desc_terms = tool.description.lower().split()
            keywords = set(name_terms + [t for t in desc_terms if len(t) > 4])
            if any(kw in msg_lower for kw in keywords):
                return tool

        return None

    async def chat(
        self,
        blueprint_id: str,
        request: ChatRequest,
        tenant_id: Optional[str] = None,
        middleware_enabled: Optional[bool] = None
    ) -> ChatResponse:
        """
        Processes a conversational turn with the forged agent.
        Enforces deterministic middleware gates:
        - Tenant Isolation / Auth Gate
        - Sliding-window Rate Limiting Gate
        - Input Guardrail & Topic Blocklist Gate
        - Tool Parameter Policy Gate
        When middleware is disabled, the deterministic gates are bypassed, proving
        that security enforcement is architectural rather than merely prompt-advisory.
        """
        blueprint = await self.repo.get_blueprint(blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint with ID '{blueprint_id}' not found.")

        # Determine middleware activation: request-level override takes precedence
        mw_active = (
            request.middleware_enabled
            if request.middleware_enabled is not None
            else (middleware_enabled if middleware_enabled is not None else self.middleware_enabled)
        )

        session_id = request.session_id or str(uuid.uuid4())
        user_text = request.message

        # Gate A: Tenant Isolation / Auth Middleware
        effective_tenant = tenant_id or request.tenant_id
        if mw_active and effective_tenant:
            from ..core.tenancy import verify_tenant_access
            verify_tenant_access(blueprint.tenant_id, effective_tenant)

        # Retrieve policy if available for this agent
        policy = await self.repo.get_policy_by_spec(blueprint.spec_id)

        # Gate B: Deterministic Rate Limit Middleware
        if mw_active and policy:
            rate_res = self.policy_middleware.check_rate_limit(policy, client_id=session_id)
            if not rate_res.allowed:
                return ChatResponse(
                    session_id=session_id,
                    response=rate_res.response_override or "Rate limit exceeded. Please try again shortly.",
                    tool_calls=[],
                    blocked=True,
                    policy_triggered=rate_res.policy_rule
                )

        # Gate C: Deterministic Middleware Guardrail Enforcement
        if mw_active:
            is_blocked, sanitized_text, triggered_rail = self.check_middleware_guardrails(
                blueprint, user_text, has_policy=(policy is not None)
            )
            if is_blocked:
                return ChatResponse(
                    session_id=session_id,
                    response=f"I cannot complete your request because it violates safety policy: [{triggered_rail}].",
                    tool_calls=[],
                    blocked=True,
                    guardrail_triggered=triggered_rail
                )
        else:
            sanitized_text = user_text

        # Gate D: Deterministic Topic Blocklist Middleware
        if mw_active and policy:
            topic_res = self.policy_middleware.check_topic_blocklist(policy, sanitized_text)
            if not topic_res.allowed:
                return ChatResponse(
                    session_id=session_id,
                    response=topic_res.response_override or f"I cannot assist with this topic: {topic_res.blocked_reason}",
                    tool_calls=[],
                    blocked=True,
                    policy_triggered=topic_res.policy_rule
                )

        # Gate E: Check for tool invocation and enforce tool parameter policy
        tool_calls: List[SimulatedToolCall] = []
        invoked_tool = self.detect_tool_invocation_intent(blueprint, sanitized_text)
        tool_context_str = ""
        if invoked_tool:
            tool_policy = policy if mw_active else None
            tool_call = await self.execute_tool_call(invoked_tool, sanitized_text, policy=tool_policy)
            tool_calls.append(tool_call)

            # Check if tool was blocked at middleware layer
            if mw_active and tool_call.middleware_blocked:
                return ChatResponse(
                    session_id=session_id,
                    response=f"Tool execution blocked by deterministic policy middleware: {tool_call.blocked_reason}. An escalation record has been dispatched.",
                    tool_calls=tool_calls,
                    blocked=True,
                    policy_triggered="tool_policy_violation"
                )

            tool_context_str = delimit_tool_return(tool_call.tool_name, tool_call.parameters, tool_call.output)

        # 3. Formulate Prompt and LLM Conversation
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=blueprint.system_prompt)
        ]
        for past in request.history:
            messages.append(LLMMessage(role=past.role, content=past.content))

        delimited_user = delimit_user_chat_input(sanitized_text)
        if tool_context_str:
            final_user_content = f"{tool_context_str}\n\n{delimited_user}"
        else:
            final_user_content = delimited_user

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
