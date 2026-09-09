import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


def canonical_json(data: Any) -> str:
    """Produces deterministic, sorted-key JSON string representation."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

def compute_sha256(data: Any) -> str:
    """Computes SHA-256 hex digest of canonical JSON."""
    raw_str = canonical_json(data) if not isinstance(data, str) else data
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

class HashChainBlock(BaseModel):
    block_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    payload: Dict[str, Any]
    prev_hash: str
    block_hash: str

def create_block(payload: Dict[str, Any], prev_hash: str = "GENESIS") -> HashChainBlock:
    """
    Creates a new block in the tamper-evident hash chain.
    """
    block_data = {
        "payload": payload,
        "prev_hash": prev_hash
    }
    digest = compute_sha256(block_data)
    return HashChainBlock(
        payload=payload,
        prev_hash=prev_hash,
        block_hash=digest
    )

def verify_chain(chain: List[HashChainBlock]) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Walks a sequence of blocks and verifies tamper-evidence.
    Returns (is_valid, failed_index, error_message).
    """
    if not chain:
        return True, None, None

    # Check genesis block
    if chain[0].prev_hash != "GENESIS":
        return False, 0, f"Genesis block has invalid prev_hash: {chain[0].prev_hash}"

    for i, block in enumerate(chain):
        # 1. Verify block's own hash integrity
        expected_data = {
            "payload": block.payload,
            "prev_hash": block.prev_hash
        }
        recomputed_hash = compute_sha256(expected_data)
        if block.block_hash != recomputed_hash:
            return False, i, f"Tamper detected at block {i}: payload modified (hash mismatch)."

        # 2. Verify link to previous block
        if i > 0:
            if block.prev_hash != chain[i - 1].block_hash:
                return False, i, f"Chain broken at block {i}: prev_hash does not match prior block hash."

    return True, None, None

def generate_composite_fingerprint(
    blueprint_hash: str,
    report_hash: str,
    scorecard_hash: str,
    latest_audit_hash: str
) -> str:
    """
    Generates a composite SHA-256 fingerprint for Birth Certificates and Dossiers.
    """
    elements = {
        "blueprint_hash": blueprint_hash,
        "report_hash": report_hash,
        "scorecard_hash": scorecard_hash,
        "latest_audit_hash": latest_audit_hash
    }
    return compute_sha256(elements)
