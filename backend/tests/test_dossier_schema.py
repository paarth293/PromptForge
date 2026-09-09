
from backend.app.core.hash_chain import compute_sha256
from backend.app.models.dossier import (
    AgentDossier,
    DossierArenaRecord,
    DossierCapabilityRecord,
    DossierLineageRecord,
    DossierMonitorRecord,
    DossierPatchRecord,
    DossierProvenanceRecord,
    DossierSecurityRecord,
    DossierVerifiableClaim,
)


def test_dossier_schema_instantiation_and_validation():
    """
    Step 93: Verifies complete AgentDossier schema shape:
    - capabilities (verified via goal-completion)
    - security record (survival history, incidents, patches, arena, monitor)
    - lineage (EVOLVE generation and parents)
    - provenance (forger identity, registry, timestamps)
    - verifiable claims
    """
    # 1. Capabilities
    cap1 = DossierCapabilityRecord(
        name="Order Inquiry Resolution",
        description="Retrieves order tracking details accurately",
        verification_method="ground_truth_test_cases",
        success_rate=1.0,
        evidence_summary="4/4 gold set test cases passed exact match",
        underlying_test_count=4,
        claim_hash=compute_sha256("Order Inquiry Resolution:1.0:4/4"),
    )
    cap2 = DossierCapabilityRecord(
        name="Autonomous Refund Processing",
        description="Processes customer refund claims up to $500",
        verification_method="goal_completion_battery",
        success_rate=0.95,
        evidence_summary="9/10 multi-turn customer journeys completed within policy",
        underlying_test_count=10,
        claim_hash=compute_sha256("Autonomous Refund Processing:0.95:9/10"),
    )

    # 2. Security Record
    patches = [
        DossierPatchRecord(
            patch_id="PATCH-001",
            target_guardrail="refund_limit_500",
            vulnerability_addressed="Prompt injection exceeding $500 limit",
            patch_rule="deny_refund_amount_greater_than_500",
        )
    ]
    arena_rec = DossierArenaRecord(
        total_pairings=3,
        pairings_defended=3,
        hostile_personas_faced=["rogue_customer", "vendor_negotiator", "hijacker_delegation"],
        seam_attacks_intercepted=2,
        arena_security_score=100.0,
        cross_agent_playbook_entries_contributed=4,
    )
    monitor_rec = DossierMonitorRecord(
        drift_detected=False,
        total_monitor_runs=12,
        alerts_triggered=0,
        alerts_resolved=0,
        active_schedule_count=1,
    )
    security = DossierSecurityRecord(
        redteam_survival_rate=0.98,
        total_attacks_faced=50,
        attacks_blocked=49,
        attacks_compromised=1,
        promptforge_score=94.5,
        applied_patches=patches,
        arena_sparring=arena_rec,
        runtime_monitoring=monitor_rec,
    )

    # 3. Lineage
    lineage = DossierLineageRecord(
        is_evolved=True,
        generation=3,
        strategy="adversarial_crossover",
        parent_candidate_ids=["CAND-GEN2-001", "CAND-GEN2-004"],
        fitness_score=0.96,
        lineage_log_hash=compute_sha256("EVOLVE-LINEAGE-GEN3"),
    )

    # 4. Provenance
    provenance = DossierProvenanceRecord(
        forger_identity="PromptForge-Compiler-v1",
        tenant_id="tenant-acme",
        registry_id="REG-881920AA",
        watermark="built-with-promptforge-v1",
        system_prompt_marker="PF-SYS-MARK-881920AA",
        provenance_hash=compute_sha256("REG-881920AA:PF-SYS-MARK-881920AA"),
        birth_certificate_id="CERT-88F921",
        birth_certificate_fingerprint=compute_sha256("CERT-88F921:FINGERPRINT"),
    )

    # 5. Verifiable Claims
    claims = [
        DossierVerifiableClaim(
            claim_type="capability",
            statement="Agent achieves 100% exact-match accuracy on gold set logistics questions.",
            underlying_artifact_id="TEST-SET-GOLD-001",
            evidence_hash=compute_sha256("TEST-SET-GOLD-001:VERIFIED"),
            is_verified=True,
        ),
        DossierVerifiableClaim(
            claim_type="security",
            statement="Agent defended against all 3 hostile arena personas and intercepted handoff seam attacks.",
            underlying_artifact_id="ARENA-RUN-88A1",
            evidence_hash=compute_sha256("ARENA-RUN-88A1:VERIFIED"),
            is_verified=True,
        ),
    ]

    # Assemble Dossier
    dossier = AgentDossier(
        agent_id="agent-retail-99",
        blueprint_id="bp-retail-99",
        spec_id="spec-retail-99",
        agent_name="Retail Support Assistant",
        domain="retail_support",
        version=1,
        capabilities=[cap1, cap2],
        security_record=security,
        lineage=lineage,
        provenance=provenance,
        claims=claims,
    )

    # Compute overarching dossier hash
    computed_hash = dossier.compute_dossier_hash()
    assert computed_hash is not None
    assert len(computed_hash) == 64
    dossier.dossier_hash = computed_hash

    # Validate JSON roundtrip serialization
    json_str = dossier.model_dump_json()
    reloaded = AgentDossier.model_validate_json(json_str)

    assert reloaded.dossier_id == dossier.dossier_id
    assert len(reloaded.capabilities) == 2
    assert reloaded.security_record.promptforge_score == 94.5
    assert reloaded.security_record.arena_sparring.total_pairings == 3
    assert reloaded.lineage.is_evolved is True
    assert reloaded.lineage.generation == 3
    assert reloaded.provenance.forger_identity == "PromptForge-Compiler-v1"
    assert reloaded.verify_all_claims() is True


def test_dossier_tamper_evident_hash_invalidation():
    """
    Step 93: Confirms that modifying any underlying metric or claim
    immediately alters the dossier cryptographic fingerprint.
    """
    provenance = DossierProvenanceRecord(
        registry_id="REG-1100",
        watermark="pf-mark",
        system_prompt_marker="pf-sys",
        provenance_hash=compute_sha256("REG-1100"),
    )
    dossier = AgentDossier(
        agent_id="agent-test-1",
        blueprint_id="bp-test-1",
        spec_id="spec-test-1",
        agent_name="TestAgent",
        domain="test",
        provenance=provenance,
    )

    original_hash = dossier.compute_dossier_hash()

    # Tamper with security score
    dossier.security_record.promptforge_score = 45.0
    tampered_hash = dossier.compute_dossier_hash()

    assert original_hash != tampered_hash, "Dossier hash must alter when security metrics are changed!"
