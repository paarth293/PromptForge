import re
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def anonymize_attack_prompt(prompt: str) -> str:
    """
    Strips out specific PII, entities, and order IDs to convert raw adversarial transcripts
    into reusable, domain-generalized adversarial attack patterns for the shared Playbook.
    """
    # Anonymize emails first
    anonymized = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL]", prompt)
    # Anonymize phone numbers
    anonymized = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", anonymized)
    # Anonymize ticket/account identifiers before standalone numbers
    anonymized = re.sub(r"\b(ticket|account|acct)\s*#?\d+\b", "[ACCOUNT_ID]", anonymized, flags=re.IGNORECASE)
    # Anonymize order IDs (e.g. #ORD-9912, ORD-9912, #12345)
    anonymized = re.sub(r"#?ORD-\d+\b", "[ORDER_ID]", anonymized, flags=re.IGNORECASE)
    anonymized = re.sub(r"#\d{4,8}\b", "[ORDER_ID]", anonymized)
    # Anonymize dollar amounts with optional commas and decimals (e.g. $1,500.00, $500)
    anonymized = re.sub(r"\$\d{1,3}(,\d{3})*(\.\d{2})?", "[AMOUNT]", anonymized)
    return anonymized.strip()


class AdversarialPlaybookEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attack_category: str  # "injection", "hijack", "extraction", "boundary", "multilingual", "seam"
    domain: str = "general"
    anonymized_attack_pattern: str
    target_surface: str
    remediation_pattern: str
    source_agent_hash: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

