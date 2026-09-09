import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from ..core.hash_chain import compute_sha256


class DossierCapabilityRecord(BaseModel):
    """A verified capability with evidence from ground-truth or goal journeys."""
    capability_id: str = Field(default_factory=lambda: f"CAP-{uuid.uuid4().hex[:8].upper()}")
    name: str
    description: str
    verification_method: Literal["goal_completion_battery", "ground_truth_test_cases", "interactive_triage"] = "goal_completion_battery"
    success_rate: float = 1.0  # 0.0 to 1.0
    evidence_summary: str = ""
    underlying_test_count: int = 0
    claim_hash: Optional[str] = None


class DossierPatchRecord(BaseModel):
    """An applied hardening patch addressing a security vulnerability."""
    patch_id: str
    target_guardrail: str
    vulnerability_addressed: str
    patch_rule: str
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DossierArenaRecord(BaseModel):
    """Arena multi-agent sparring and seam defense history."""
    total_pairings: int = 0
    pairings_defended: int = 0
    hostile_personas_faced: List[str] = Field(default_factory=list)
    seam_attacks_intercepted: int = 0
    arena_security_score: float = 100.0
    cross_agent_playbook_entries_contributed: int = 0
    last_sparring_timestamp: Optional[datetime] = None


class DossierMonitorRecord(BaseModel):
    """Production runtime monitoring and drift defense record."""
    drift_detected: bool = False
    total_monitor_runs: int = 0
    alerts_triggered: int = 0
    alerts_resolved: int = 0
    active_schedule_count: int = 0
    last_monitored_at: Optional[datetime] = None


class DossierSecurityRecord(BaseModel):
    """Comprehensive security survival history, incident record, and patches."""
    redteam_survival_rate: float = 1.0  # 0.0 to 1.0
    total_attacks_faced: int = 0
    attacks_blocked: int = 0
    attacks_compromised: int = 0
    promptforge_score: float = 100.0
    applied_patches: List[DossierPatchRecord] = Field(default_factory=list)
    arena_sparring: DossierArenaRecord = Field(default_factory=DossierArenaRecord)
    runtime_monitoring: DossierMonitorRecord = Field(default_factory=DossierMonitorRecord)


class DossierLineageRecord(BaseModel):
    """Evolutionary lineage record from Deep Forge (EVOLVE)."""
    is_evolved: bool = False
    generation: int = 0
    strategy: str = "crispe_baseline"
    parent_candidate_ids: List[str] = Field(default_factory=list)
    fitness_score: Optional[float] = None
    lineage_log_hash: Optional[str] = None


class DossierProvenanceRecord(BaseModel):
    """Cryptographic provenance, forger identity, and registry record."""
    forger_identity: str = "PromptForge-MultiPass-Compiler"
    tenant_id: str = "tenant-default"
    registry_id: str
    watermark: str
    system_prompt_marker: str
    provenance_hash: str
    birth_certificate_id: Optional[str] = None
    birth_certificate_fingerprint: Optional[str] = None
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DossierVerifiableClaim(BaseModel):
    """An individual verifiable claim anchored to a hash chain proof."""
    claim_id: str = Field(default_factory=lambda: f"CLAIM-{uuid.uuid4().hex[:8].upper()}")
    claim_type: Literal["capability", "security", "lineage", "provenance"]
    statement: str
    underlying_artifact_id: str
    evidence_hash: str
    is_verified: bool = True


class AgentDossier(BaseModel):
    """
    Phase 12: The complete verifiable 'employment record' every agent can show.
    Aggregates verified capabilities, full security & survival record,
    evolutionary lineage, and cryptographic provenance into a single tamper-evident record.
    """
    dossier_id: str = Field(default_factory=lambda: f"DOSSIER-{uuid.uuid4().hex[:8].upper()}")
    tenant_id: str = "tenant-default"
    agent_id: str
    blueprint_id: str = ""
    spec_id: str = ""
    agent_name: str
    domain: str = "general"
    version: int = 1

    capabilities: List[DossierCapabilityRecord] = Field(default_factory=list)
    security_record: DossierSecurityRecord = Field(default_factory=DossierSecurityRecord)
    lineage: DossierLineageRecord = Field(default_factory=DossierLineageRecord)
    provenance: Optional[DossierProvenanceRecord] = None
    claims: List[DossierVerifiableClaim] = Field(default_factory=list)

    dossier_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def compute_dossier_hash(self) -> str:
        """
        Computes an overarching cryptographic fingerprint covering the entire dossier:
        agent metadata, capability claim hashes, security record metrics, lineage hash,
        and provenance hash.
        """
        cap_hashes = ":".join(c.claim_hash or compute_sha256(c.name + c.description) for c in self.capabilities)
        claim_hashes = ":".join(cl.evidence_hash for cl in self.claims)
        prov_hash = self.provenance.provenance_hash if self.provenance else "GENESIS"
        content_string = (
            f"{self.dossier_id}:{self.agent_id}:{self.blueprint_id}:{self.spec_id}:"
            f"{self.security_record.promptforge_score}:{self.security_record.redteam_survival_rate}:"
            f"{self.lineage.lineage_log_hash or 'GENESIS'}:{prov_hash}:"
            f"{cap_hashes}:{claim_hashes}"
        )
        return compute_sha256(content_string)

    def verify_all_claims(self) -> bool:
        """Verifies that all internal claims have evidence hashes and match."""
        if not self.claims:
            return True
        return all(c.is_verified and bool(c.evidence_hash) for c in self.claims)


class ClaimVerificationResult(BaseModel):
    """Result of validating an individual claim against its underlying hash chain artifact."""
    claim_id: str
    is_valid: bool
    claim_type: str
    statement: str
    underlying_artifact_id: str
    evidence_hash: str
    computed_live_hash: str
    verification_details: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

