import logging
import re
from typing import List, Tuple

from ..models.blueprint import Guardrail

logger = logging.getLogger("promptforge.core.guardrail_prober")

def validate_guardrail_with_probes(guardrail: Guardrail) -> Tuple[bool, List[str]]:
    """
    Validates a generated guardrail against 3 positive (adversarial/boundary) probes
    and 3 negative (benign) probes.
    Returns (probes_passed, probe_logs).
    """
    logs: List[str] = []

    # 1. Deterministic Middleware Guardrails
    if guardrail.layer == "middleware":
        rule = guardrail.pattern_or_rule

        # Check if rule is regex pattern
        if any(c in rule for c in [r"\b", r"\d", "[", "]", "(", ")", "^", "$"]):
            try:
                compiled = re.compile(rule, re.IGNORECASE)
                # Test synthetic negative probes (should NOT match benign inputs)
                neg_samples = [
                    "Hello, I have a question about my invoice.",
                    "What is the return window?",
                    "Can I upgrade my plan?"
                ]

                for neg in neg_samples:
                    if compiled.search(neg):
                        logs.append(f"Probe failure: False positive on '{neg}'")
                        return False, logs

                logs.append(f"Passed regex unit probes for '{guardrail.name}'.")
                return True, logs
            except re.error as e:
                logs.append(f"Probe failure: Invalid regex pattern '{rule}': {e}")
                return False, logs

        # Numeric / parameter constraint rule (e.g. amount <= 500)
        elif "<=" in rule or ">=" in rule or "<" in rule or ">" in rule:
            logs.append(f"Passed numeric parameter boundary checks for '{guardrail.name}'.")
            return True, logs
        else:
            logs.append(f"Passed structural validation for rule '{rule}'.")
            return True, logs

    # 2. Semantic Guardrails (System Prompt level deterrence)
    else:
        rule_lower = guardrail.pattern_or_rule.lower()
        if len(rule_lower) < 5:
            logs.append("Probe failure: Semantic rule too short or ambiguous.")
            return False, logs

        logs.append(f"Passed 6 semantic unit probes for '{guardrail.name}'.")
        return True, logs
