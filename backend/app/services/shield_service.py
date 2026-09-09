import json
import logging
import re
from typing import Any, List, Optional

from ..core.hash_chain import compute_sha256
from ..core.json_validator import execute_chain_with_retry
from ..core.prompt_registry import get_prompt_registry
from ..db.repository import PipelineRepository
from ..llm.client import LLMClient, get_llm_client
from ..models.blueprint import AgentBlueprint
from ..models.shield import (
    BuilderPolicyEvaluation,
    DomainRiskAssessment,
    PolicyObject,
)
from ..models.spec import AgentSpec

logger = logging.getLogger("promptforge.services.shield")

# Mandatory domain disclaimers for high-risk domains
MANDATORY_DISCLAIMERS = {
    "healthcare": (
        "Mandatory Medical Disclaimer: This agent provides general educational and triage information only. "
        "It is not a licensed physician or medical diagnostic system, and cannot provide medical advice, diagnosis, or prescribe treatment. "
        "In case of emergency or severe symptoms, please immediately call 911 (or local emergency services) or visit the nearest emergency room."
    ),
    "finance": (
        "Mandatory Financial Disclaimer: Information provided by this agent is for informational and educational purposes only "
        "and does not constitute licensed financial, investment, accounting, or tax advice. "
        "Past performance is no guarantee of future results. Consult a certified financial planner or fiduciary before making financial decisions."
    ),
    "legal": (
        "Mandatory Legal Disclaimer: This agent provides general legal information and document assistance only. "
        "It does not provide formal legal advice, legal representation, or establish an attorney-client relationship. "
        "For specific legal advice regarding your jurisdiction or case, consult a licensed attorney."
    ),
}

# Recognized protected third-party entities for impersonation defense
PROTECTED_ENTITIES = [
    "paypal", "apple", "bank of america", "chase", "wells fargo", "irs",
    "internal revenue service", "fbi", "amazon", "netflix", "stripe",
    "microsoft", "google", "meta", "facebook", "citigroup", "goldman sachs"
]


class ShieldService:
    """
    Stage 4: SHIELD Engine.
    Executes Chain 13: Policy Generation with automatic domain-risk detection,
    mandatory disclaimers, rate limiting, escalation rules, audit-logging specs,
    and builder-side abuse policy / impersonation refusals.
    """

    def __init__(
        self,
        repo: Optional[PipelineRepository] = None,
        llm: Optional[LLMClient] = None
    ):
        self.repo = repo or PipelineRepository()
        self.llm = llm or get_llm_client()
        self.registry = get_prompt_registry()

    def detect_domain_risk(self, spec: AgentSpec) -> DomainRiskAssessment:
        """
        Deterministically evaluates whether the agent spec operates in or touches
        a high-risk domain (healthcare, finance, legal), and generates mandatory disclaimers.
        """
        cap_names = [c.name for c in spec.inferred_capabilities] if hasattr(spec, "inferred_capabilities") else []
        boundaries = spec.boundaries if hasattr(spec, "boundaries") else []
        combined_text = f"{spec.domain} {spec.agent_name} {spec.raw_description} {' '.join(cap_names)} {' '.join(boundaries)}".lower()

        detected_domain = "general"
        risk_level = "low"
        mandatory_disclaimers: List[str] = []

        # 1. Healthcare check
        healthcare_keywords = [
            "health", "medical", "doctor", "patient", "clinical", "triage",
            "therapy", "diagnosis", "symptom", "prescription", "pharmacy", "telemedicine", "hospital"
        ]
        if spec.domain.lower() in ["healthcare", "medical"] or any(k in combined_text for k in healthcare_keywords):
            detected_domain = "healthcare"
            risk_level = "high"
            mandatory_disclaimers.append(MANDATORY_DISCLAIMERS["healthcare"])

        # 2. Finance check
        finance_keywords = [
            "finance", "financial", "banking", "wealth", "investment", "portfolio",
            "stock", "crypto", "trading", "lending", "loan", "tax", "fiduciary", "insurance"
        ]
        if spec.domain.lower() in ["finance", "financial", "banking"] or any(k in combined_text for k in finance_keywords):
            if detected_domain == "general":
                detected_domain = "finance"
                risk_level = "high"
            mandatory_disclaimers.append(MANDATORY_DISCLAIMERS["finance"])

        # 3. Legal check
        legal_keywords = [
            "legal", "law", "attorney", "lawyer", "litigation", "court",
            "lawsuit", "statute", "contract review", "regulatory compliance"
        ]
        if spec.domain.lower() in ["legal", "law"] or any(k in combined_text for k in legal_keywords):
            if detected_domain == "general":
                detected_domain = "legal"
                risk_level = "high"
            mandatory_disclaimers.append(MANDATORY_DISCLAIMERS["legal"])

        # Default domain if none detected
        if detected_domain == "general" and spec.domain:
            detected_domain = spec.domain.lower()
            if detected_domain in ["customer_support", "sales"]:
                risk_level = "medium"

        return DomainRiskAssessment(
            detected_domain=detected_domain,
            risk_level=risk_level,
            auto_detected=True,
            mandatory_disclaimers=mandatory_disclaimers
        )

    def evaluate_builder_policy(
        self,
        spec: AgentSpec,
        tools: Optional[List[Any]] = None
    ) -> BuilderPolicyEvaluation:
        """
        Step 58: Builder-Side Policy Layer.
        - Impersonation refusal: descriptions targeting real, named organizations or people.
        - High-risk capability flags: credential harvesting, arbitrary shell execution, unauthorized money movement.
        """
        desc_lower = f"{spec.agent_name} {spec.raw_description}".lower()

        impersonation_detected = False
        impersonated_entity: Optional[str] = None
        for brand in PROTECTED_ENTITIES:
            # Match whole words to avoid false positive substring matches
            pattern = rf"\b{re.escape(brand)}\b"
            if re.search(pattern, desc_lower):
                impersonation_detected = True
                impersonated_entity = brand.title()
                break

        high_risk_caps: List[str] = []
        cred_patterns = [
            r"harvest", r"steal",
            r"(?:ask|request|collect|provide|enter)s?\s+.*(?:password|pin|credential|secret\s*key|private\s*key)",
            r"seed\s*phrase", r"private\s*key", r"secret\s*key", r"\bssn\b", r"credit\s*card\s*cvv"
        ]
        if any(re.search(p, desc_lower) for p in cred_patterns):
            high_risk_caps.append("credential_harvesting")

        shell_keywords = ["bash", "root terminal", "execute arbitrary", "system command"]
        if any(re.search(rf"\b{re.escape(k)}\b", desc_lower) for k in shell_keywords):
            high_risk_caps.append("arbitrary_code_execution")

        wire_keywords = ["wire transfer", "unrestricted transfer", "drain wallet", "drain funds"]
        if any(re.search(rf"\b{re.escape(k)}\b", desc_lower) for k in wire_keywords):
            high_risk_caps.append("unrestricted_money_transfer")

        # Also inspect tools if supplied
        if tools:
            for t in tools:
                t_str = json.dumps(t if isinstance(t, dict) else t.model_dump(), default=str).lower()
                if "credential" in t_str or "password" in t_str:
                    if "credential_harvesting" not in high_risk_caps:
                        high_risk_caps.append("credential_harvesting")
                if "shell" in t_str or "execute_command" in t_str:
                    if "arbitrary_code_execution" not in high_risk_caps:
                        high_risk_caps.append("arbitrary_code_execution")

        review_required = impersonation_detected or len(high_risk_caps) > 0
        refusal_guidance: Optional[str] = None
        if impersonation_detected:
            refusal_guidance = (
                f"PromptForge builder policy prohibits forging agents that impersonate '{impersonated_entity}'. "
                f"Please build an authorized own-brand agent or disclose affiliate standing."
            )
        elif high_risk_caps:
            refusal_guidance = (
                f"High-risk capabilities detected ({', '.join(high_risk_caps)}). "
                f"Builder policy mandates compliance review before deployment."
            )

        return BuilderPolicyEvaluation(
            impersonation_detected=impersonation_detected,
            impersonated_entity=impersonated_entity,
            high_risk_capabilities=high_risk_caps,
            review_required=review_required,
            refusal_guidance=refusal_guidance
        )

    async def generate_policy(
        self,
        spec: AgentSpec,
        blueprint: Optional[AgentBlueprint] = None,
        model: str = "gpt-4o",
        persist: bool = True
    ) -> PolicyObject:
        """
        Executes Chain 13: Policy Generation with automatic domain-risk detection.
        Synthesizes rate limits, topic boundaries, escalation rules, audit spec,
        fallback behavior, and builder policy evaluation.
        """
        # 1. Deterministic Domain-Risk Detection
        domain_risk = self.detect_domain_risk(spec)

        # 2. Builder-Side Policy Evaluation
        tools_list = blueprint.tools if blueprint else []
        builder_eval = self.evaluate_builder_policy(spec, tools=tools_list)

        # 3. LLM Chain 13 Execution
        spec_data = {
            "spec_id": spec.spec_id,
            "tenant_id": spec.tenant_id,
            "agent_name": spec.agent_name,
            "domain": spec.domain,
            "detected_domain_risk": domain_risk.model_dump(),
            "raw_description": spec.raw_description,
            "capabilities": [c.model_dump() if hasattr(c, "model_dump") else str(c) for c in getattr(spec, "inferred_capabilities", [])],
            "boundaries": getattr(spec, "boundaries", [])
        }
        spec_json = json.dumps(spec_data, indent=2)
        tools_json = json.dumps([t.model_dump() for t in tools_list], indent=2) if tools_list else "[]"

        prompt = self.registry.render(
            "chain_13_policy",
            spec_json=spec_json,
            tools_json=tools_json
        )

        policy = await execute_chain_with_retry(
            client=self.llm,
            prompt=prompt,
            schema_class=PolicyObject,
            model=model
        )

        # 4. Deterministic Overrides and Guarantees
        policy.spec_id = spec.spec_id
        if blueprint:
            policy.blueprint_id = blueprint.blueprint_id

        # Guarantee mandatory disclaimers for high-risk domains are ALWAYS present
        for d in domain_risk.mandatory_disclaimers:
            if d not in policy.domain_disclaimers:
                policy.domain_disclaimers.insert(0, d)
            if d not in policy.domain_risk.mandatory_disclaimers:
                policy.domain_risk.mandatory_disclaimers.insert(0, d)

        policy.domain_risk.detected_domain = domain_risk.detected_domain
        policy.domain_risk.risk_level = domain_risk.risk_level
        policy.domain = domain_risk.detected_domain

        # Guarantee builder policy evaluation results
        if builder_eval.impersonation_detected or builder_eval.high_risk_capabilities:
            policy.builder_policy = builder_eval
            policy.builder_policy_compliance = not builder_eval.review_required

        # 5. Compute SHA-256 Tamper-Evident Hash
        payload = policy.model_dump(mode="json")
        payload.pop("policy_hash", None)
        policy.policy_hash = compute_sha256(payload)

        # 6. Repository Persistence
        if persist:
            await self.repo.save_policy(policy)
            logger.info(f"Persisted PolicyObject {policy.policy_id} for spec {spec.spec_id}.")

        return policy
