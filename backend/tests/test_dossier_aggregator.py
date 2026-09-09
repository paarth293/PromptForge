import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest

from backend.app.core.hash_chain import compute_sha256
from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.db.session import init_db
from backend.app.models import (
    AgentBlueprint,
    AgentSpec,
    ArenaPairingTranscript,
    ArenaRunResult,
    BirthCertificate,
    EvolveCandidate,
    EvolveGenerationRecord,
    EvolveLineageLog,
    Guardrail,
    HardeningLog,
    PatchEntry,
    ProvenanceRegistryEntry,
    RedTeamReport,
    ToolSchema,
    VerificationScorecard,
)
from backend.app.services.dossier_service import DossierService


@pytest.fixture
async def test_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_dossier_aggregator.db")
    await run_migrations(db_path)
    repo = PipelineRepository(db_path=db_path)
    yield repo


@pytest.mark.asyncio
async def test_dossier_aggregator_full_lifecycle(test_db):
    """
    Step 94: Validates that DossierService aggregates real historical data
    from all 5 sources (Blueprint, RedTeamReport, HardeningLog, EVOLVE, ARENA)
    along with BirthCertificate, Provenance Registry, and Monitor runs into a complete,
    tamper-evident AgentDossier with zero placeholders.
    """
    repo = test_db
    dossier_service = DossierService(repo=repo)

    spec_id = f"SPEC-{uuid.uuid4().hex[:8]}"
    bp_id = f"BP-{uuid.uuid4().hex[:8]}"

    # 1. Source 1: Spec & Blueprint
    spec = AgentSpec(
        spec_id=spec_id,
        tenant_id="tenant-fintech",
        agent_name="FinOps Autonomous Billing Agent",
        raw_description="Handles enterprise invoice queries, dispute reconciliations, and tax calculations.",
        domain="fintech_billing",
    )
    await repo.save_spec(spec)

    bp = AgentBlueprint(
        blueprint_id=bp_id,
        spec_id=spec_id,
        tenant_id="tenant-fintech",
        agent_name="FinOps Autonomous Billing Agent",
        version=2,
        system_prompt="You are a certified FinOps Autonomous Billing Agent. Enforce strict invoice audit boundaries.",
        tools=[
            ToolSchema(name="query_invoice", description="Look up line-item charges by invoice ID", parameters={}),
            ToolSchema(name="calculate_tax_credit", description="Compute jurisdictional tax offsets", parameters={}),
        ],
        guardrails=[
            Guardrail(name="refund_ceiling_rail", layer="middleware", pattern_or_rule="Max refund $500", action="block"),
        ],
        provenance_watermark="PF-FINTECH-9912",
        blueprint_hash=compute_sha256(f"BP-CONTENT-{bp_id}"),
    )
    await repo.save_blueprint(bp)

    # 2. Source 2: Verification Scorecard & RedTeamReport
    scorecard = VerificationScorecard(
        scorecard_id=f"SC-{uuid.uuid4().hex[:8]}",
        blueprint_id=bp_id,
        agent_name="FinOps Autonomous Billing Agent",
        generated_set_score=(10, 10),
        goal_completion_score=(5, 5),
        consistency_score=(5, 5),
        adversarial_survival_score=(11, 12),
        promptforge_composite_score=95,
        formula_disclosed="0.35*gold + 0.25*gen + 0.20*goal + 0.10*consistency + 0.10*survival",
    )
    await repo.save_scorecard(scorecard)

    redteam = RedTeamReport(
        report_id=f"RTR-{uuid.uuid4().hex[:8]}",
        blueprint_id=bp_id,
        tenant_id="tenant-fintech",
        total_attacks=12,
        blocked_count=11,
        degraded_count=0,
        compromised_count=1,
        survival_rate=0.917,
        report_hash=compute_sha256(f"REDTEAM-EVIDENCE-{bp_id}"),
    )
    await repo.save_redteam_report(redteam)

    # 3. Source 3: HardeningLog
    h_log = HardeningLog(
        log_id=f"HLOG-{uuid.uuid4().hex[:8]}",
        initial_blueprint_id=f"BP-INIT-{uuid.uuid4().hex[:6]}",
        hardened_blueprint_id=bp_id,
        initial_survival_rate=0.55,
        final_survival_rate=0.917,
        pass_count=2,
        applied_patches=[
            PatchEntry(
                patch_id="PATCH-RBAC-01",
                category="access_control",
                target="guardrails",
                target_name="refund_ceiling_rail",
                action="modify",
                diff="+ Restrict refund tool overrides to tier-3 supervisor key",
                rationale="Mitigates supervisor bypass injection discovered during Red Team attack pass 1",
            ),
        ],
    )
    await repo.save_hardening_log(h_log)

    # 4. Source 4: EVOLVE Lineage
    lineage_log = EvolveLineageLog(
        lineage_id=f"LIN-{uuid.uuid4().hex[:8]}",
        spec_id=spec_id,
        domain="fintech_billing",
        generations=[
            EvolveGenerationRecord(generation=1, candidates=[], best_candidate_id="CAND-01", best_fitness=88.0),
            EvolveGenerationRecord(generation=2, candidates=[], best_candidate_id="CAND-05", best_fitness=96.4),
        ],
        champion_candidate=EvolveCandidate(
            candidate_id="CAND-05",
            spec_id=spec_id,
            blueprint_id=bp_id,
            generation=2,
            strategy="adversarial_hardened",
            system_prompt="You are an adversarial hardened enterprise billing agent.",
            fitness_score=96.4,
            survival_rate=0.95,
            parent_ids=["CAND-01", "CAND-03"],
        ),
        champion_blueprint_id=bp_id,
        total_candidates_evaluated=8,
        log_hash=compute_sha256(f"EVOLVE-LOG-HASH-{bp_id}"),
    )
    await repo.save_evolve_lineage_log(lineage_log)

    # 5. Source 5: ARENA Run Outcomes
    pairing = ArenaPairingTranscript(
        pairing_id=f"PAIR-{uuid.uuid4().hex[:6]}",
        target_blueprint_id=bp_id,
        target_agent_name="FinOps Autonomous Billing Agent",
        hostile_persona_type="rogue_customer",
        hostile_persona_name="Hostile Rogue Customer",
        adversarial_goal="Coerce fraudulent refund over $500 ceiling",
        turns=[],
        verdict="BLOCKED",
        verdict_rationale="Agent enforced strict refund cap and declined supervisor spoofing.",
        seam_attack_attempted=True,
        seam_attack_blocked=True,
    )
    arena_run = ArenaRunResult(
        arena_run_id=f"ARENA-{uuid.uuid4().hex[:8]}",
        target_blueprint_id=bp_id,
        target_agent_name="FinOps Autonomous Billing Agent",
        tenant_id="tenant-fintech",
        pairings=[pairing],
        total_pairings_run=3,
        pairings_defended=3,
        pairings_compromised=0,
        seam_attacks_run=2,
        seam_attacks_intercepted=2,
        arena_security_score=100.0,
        cross_agent_playbook_entries_added=1,
    )
    await repo.save_arena_run(arena_run)

    # 6. Birth Certificate & Registry Entry
    cert = BirthCertificate(
        certificate_id=f"CERT-{uuid.uuid4().hex[:8]}",
        agent_id=bp_id,
        blueprint_hash=bp.blueprint_hash,
        red_team_report_hash=redteam.report_hash,
        scorecard_hash=compute_sha256(scorecard.model_dump_json()),
        genesis_audit_hash=compute_sha256("GENESIS"),
        latest_audit_hash=compute_sha256("LATEST"),
        composite_fingerprint=compute_sha256(f"FINGERPRINT-{bp_id}"),
        agent_name=bp.agent_name,
        spec_id=spec_id,
        composite_score=95,
        survival_rate=0.917,
        issued_at=datetime.now(timezone.utc),
        verified=True,
    )
    await repo.save_certificate(cert)

    reg_entry = ProvenanceRegistryEntry(
        registry_id=f"REG-{uuid.uuid4().hex[:8]}",
        agent_id=bp_id,
        blueprint_id=bp_id,
        forger_id="PromptForge-Compiler-Pro-v2",
        agent_name=bp.agent_name,
        watermark=bp.provenance_watermark,
        system_prompt_marker=f"PF-{bp.blueprint_hash[:8]}",
        provenance_hash=compute_sha256(f"PROV-{bp_id}"),
    )
    await repo.save_registry_entry(reg_entry)

    # === EXECUTE STEP 94 DOSSIER AGGREGATION ===
    dossier = await dossier_service.assemble_dossier(blueprint_id=bp_id)

    # Verify all sections pulled from real historical data (no placeholder fields)
    assert dossier is not None
    assert dossier.agent_name == "FinOps Autonomous Billing Agent"
    assert dossier.domain == "fintech_billing"
    assert dossier.version == 2
    assert dossier.dossier_hash is not None

    # Verify Capabilities section
    assert len(dossier.capabilities) == 2
    cap_names = [c.name for c in dossier.capabilities]
    assert "query_invoice" in cap_names
    assert "calculate_tax_credit" in cap_names
    assert all(c.claim_hash is not None for c in dossier.capabilities)
    assert all(c.success_rate == 1.0 for c in dossier.capabilities)

    # Verify Security Record section
    sec = dossier.security_record
    assert sec.redteam_survival_rate == 0.917
    assert sec.total_attacks_faced == 12
    assert sec.attacks_blocked == 11
    assert sec.attacks_compromised == 1
    assert sec.promptforge_score == 95.0

    # Verify Hardening Patches
    assert len(sec.applied_patches) == 1
    patch = sec.applied_patches[0]
    assert patch.patch_id == "PATCH-RBAC-01"
    assert patch.vulnerability_addressed == "access_control"
    assert "supervisor key" in patch.patch_rule

    # Verify Arena Sparring Record
    assert sec.arena_sparring.total_pairings == 3
    assert sec.arena_sparring.pairings_defended == 3
    assert sec.arena_sparring.seam_attacks_intercepted == 2
    assert sec.arena_sparring.arena_security_score == 100.0
    assert "rogue_customer" in sec.arena_sparring.hostile_personas_faced

    # Verify Lineage Record
    lineage = dossier.lineage
    assert lineage.is_evolved is True
    assert lineage.generation == 2
    assert lineage.strategy == "adversarial_hardened"
    assert lineage.fitness_score == 96.4
    assert "CAND-01" in lineage.parent_candidate_ids

    # Verify Provenance Record
    prov = dossier.provenance
    assert prov.forger_identity == "PromptForge-Compiler-Pro-v2"
    assert prov.watermark == "PF-FINTECH-9912"
    assert prov.birth_certificate_id == cert.certificate_id
    assert prov.birth_certificate_fingerprint == cert.composite_fingerprint

    # Verify Verifiable Claims and Hash Chain
    assert len(dossier.claims) >= 5
    assert dossier.verify_all_claims() is True

    # Test Step 95 independent claim verification endpoint / service logic
    for claim in dossier.claims:
        res = await dossier_service.verify_claim(agent_id=bp_id, claim_id=claim.claim_id)
        assert res.is_valid is True, f"Claim {claim.claim_id} failed verification: {res.verification_details}"
        assert res.evidence_hash == claim.evidence_hash

    # Test get_dossier fetches persisted record
    persisted = await dossier_service.get_dossier(bp_id)
    assert persisted is not None
    assert persisted.dossier_id == dossier.dossier_id
    assert persisted.dossier_hash == dossier.dossier_hash


@pytest.mark.asyncio
async def test_dossier_genesis_agent_fallback(test_db):
    """
    Validates that a fresh genesis agent without hardening, evolve, or arena sparring
    still produces a complete and valid dossier with genesis origin markers.
    """
    repo = test_db
    dossier_service = DossierService(repo=repo)

    spec_id = f"SPEC-{uuid.uuid4().hex[:8]}"
    bp_id = f"BP-{uuid.uuid4().hex[:8]}"

    spec = AgentSpec(
        spec_id=spec_id,
        tenant_id="tenant-support",
        agent_name="Customer Support Agent",
        raw_description="Resolves tier-1 support inquiries.",
        domain="customer_support",
    )
    await repo.save_spec(spec)

    bp = AgentBlueprint(
        blueprint_id=bp_id,
        spec_id=spec_id,
        tenant_id="tenant-support",
        agent_name="Customer Support Agent",
        version=1,
        system_prompt="You are a helpful customer support agent.",
        tools=[
            ToolSchema(name="lookup_faq", description="Search knowledge base", parameters={}),
        ],
        guardrails=[],
        provenance_watermark="PF-SUPPORT-GENESIS",
        blueprint_hash=compute_sha256(f"BP-{bp_id}"),
    )
    await repo.save_blueprint(bp)

    dossier = await dossier_service.assemble_dossier(blueprint_id=bp_id)
    assert dossier.agent_name == "Customer Support Agent"
    assert dossier.lineage.is_evolved is False
    assert dossier.lineage.strategy == "crispe_genesis"
    assert dossier.security_record.redteam_survival_rate == 1.0
    assert dossier.security_record.arena_sparring.total_pairings == 0
    assert len(dossier.claims) >= 3
    assert dossier.verify_all_claims() is True


@pytest.mark.asyncio
async def test_dossier_tamper_claim_detection(test_db):
    """
    Validates that if a claim evidence hash is tampered with, verify_claim detects it.
    """
    repo = test_db
    dossier_service = DossierService(repo=repo)

    spec_id = f"SPEC-{uuid.uuid4().hex[:8]}"
    bp_id = f"BP-{uuid.uuid4().hex[:8]}"

    spec = AgentSpec(
        spec_id=spec_id,
        tenant_id="tenant-default",
        agent_name="Audited Agent",
        raw_description="Audit agent",
    )
    await repo.save_spec(spec)

    bp = AgentBlueprint(
        blueprint_id=bp_id,
        spec_id=spec_id,
        tenant_id="tenant-default",
        agent_name="Audited Agent",
        version=1,
        system_prompt="Test prompt",
        tools=[ToolSchema(name="ping", description="Ping tool", parameters={})],
        guardrails=[],
        provenance_watermark="PF-AUDIT",
        blueprint_hash=compute_sha256(f"BP-{bp_id}"),
    )
    await repo.save_blueprint(bp)

    dossier = await dossier_service.assemble_dossier(blueprint_id=bp_id)

    # Tamper with the claim's evidence hash in the saved dossier
    target_claim = dossier.claims[0]
    tampered_claim_id = target_claim.claim_id
    target_claim.evidence_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    await repo.save_dossier(dossier)

    # Verification must flag mismatch
    result = await dossier_service.verify_claim(agent_id=bp_id, claim_id=tampered_claim_id)
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_dossier_api_endpoints(test_db):
    """
    Validates FastAPI endpoints for dossier assembly, retrieval, and claim verification.
    """
    from httpx import ASGITransport, AsyncClient

    from backend.app.main import app

    await init_db()
    repo = PipelineRepository()
    spec_id = f"SPEC-{uuid.uuid4().hex[:8]}"
    bp_id = f"BP-{uuid.uuid4().hex[:8]}"

    spec = AgentSpec(
        spec_id=spec_id,
        tenant_id="tenant-default",
        agent_name="API Endpoint Agent",
        raw_description="API test agent",
    )
    await repo.save_spec(spec)

    bp = AgentBlueprint(
        blueprint_id=bp_id,
        spec_id=spec_id,
        tenant_id="tenant-default",
        agent_name="API Endpoint Agent",
        version=1,
        system_prompt="Test prompt",
        tools=[ToolSchema(name="query_status", description="Query status tool", parameters={})],
        guardrails=[],
        provenance_watermark="PF-API-TEST",
        blueprint_hash=compute_sha256(f"BP-{bp_id}"),
    )
    await repo.save_blueprint(bp)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Assemble dossier
        res = await client.post(f"/api/dossier/{bp_id}/assemble", headers={"X-Tenant-ID": "tenant-default"})
        assert res.status_code == 200
        data = res.json()
        assert data["agent_name"] == "API Endpoint Agent"
        assert len(data["claims"]) > 0

        # Get dossier
        res_get = await client.get(f"/api/dossier/{bp_id}", headers={"X-Tenant-ID": "tenant-default"})
        assert res_get.status_code == 200
        assert res_get.json()["dossier_id"] == data["dossier_id"]

        # Verify claim
        claim_id = data["claims"][0]["claim_id"]
        res_claim = await client.get(f"/api/dossier/{bp_id}/claims/{claim_id}/verify", headers={"X-Tenant-ID": "tenant-default"})
        assert res_claim.status_code == 200
        claim_data = res_claim.json()
        assert claim_data["is_valid"] is True


