import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.db.session import DB_PATH
from backend.app.main import app
from backend.app.models import (
    AgentBlueprint,
    AgentDossier,
    AgentSpec,
    ArenaRunResult,
    BirthCertificate,
    EvolveCandidate,
    EvolveGenerationRecord,
    EvolveLineageLog,
    HardeningLog,
    PatchEntry,
    RedTeamReport,
    VerificationScorecard,
)
from backend.app.models.dossier import DossierProvenanceRecord


@pytest.mark.asyncio
async def test_cross_tenant_access_rejected_with_404():
    """
    Step 98: Comprehensive Tenant Isolation Audit.
    Validates that cross-tenant access to every stored object type
    (Specs, Blueprints, HardeningLogs, VerificationScorecards, BirthCertificates,
     RedTeamReports, Monitor, EvolutionNodes, ArenaTournaments, Dossiers)
    is strictly rejected with HTTP 404 (Not Found) to avoid leaking existence.
    """
    await run_migrations(DB_PATH)
    repo = PipelineRepository()

    tenant_a = "tenant-alpha-enterprise"
    tenant_b = "tenant-beta-adversary"

    # 1. Spec
    spec_a = AgentSpec(
        spec_id="spec-iso-001",
        tenant_id=tenant_a,
        agent_name="Isolated_Alpha_Agent",
        raw_description="Top-secret banking triage agent",
        domain="finance",
    )
    await repo.save_spec(spec_a)

    # 2. Blueprint
    bp_a = AgentBlueprint(
        blueprint_id="bp-iso-001",
        spec_id=spec_a.spec_id,
        tenant_id=tenant_a,
        version=1,
        agent_name="Isolated_Alpha_Agent",
        blueprint_hash="hash-alpha-blueprint-001",
        system_prompt="Strictly confidential Alpha banking logic",
    )
    await repo.save_blueprint(bp_a)

    # 3. RedTeamReport
    report_a = RedTeamReport(
        report_id="rt-iso-001",
        blueprint_id=bp_a.blueprint_id,
        tenant_id=tenant_a,
        survival_rate=0.95,
        total_attacks=20,
        blocked_count=19,
        degraded_count=0,
        compromised_count=1,
    )
    await repo.save_redteam_report(report_a)

    # 4. HardeningLog
    hlog_a = HardeningLog(
        log_id="hlog-iso-001",
        tenant_id=tenant_a,
        initial_blueprint_id=bp_a.blueprint_id,
        hardened_blueprint_id=bp_a.blueprint_id,
        initial_survival_rate=0.60,
        final_survival_rate=0.95,
        pass_count=2,
        applied_patches=[
            PatchEntry(
                category="prompt_injection",
                target="system_prompt",
                action="append",
                diff="+ Refuse non-alpha tenants",
                rationale="Strict boundary enforcement",
            )
        ],
    )
    await repo.save_hardening_log(hlog_a)

    # 5. VerificationScorecard
    card_a = VerificationScorecard(
        scorecard_id="sc-iso-001",
        tenant_id=tenant_a,
        blueprint_id=bp_a.blueprint_id,
        agent_name="Isolated_Alpha_Agent",
        generated_set_score=(10, 10),
        goal_completion_score=(10, 10),
        consistency_score=(5, 5),
        adversarial_survival_score=(20, 20),
        promptforge_composite_score=98,
        formula_disclosed="Composite Formula 1.0",
    )
    await repo.save_scorecard(card_a)

    # 6. BirthCertificate
    cert_a = BirthCertificate(
        certificate_id="cert-iso-001",
        tenant_id=tenant_a,
        agent_id=bp_a.blueprint_id,
        blueprint_hash="hash-alpha-blueprint-001",
        red_team_report_hash="hash-rt-001",
        scorecard_hash="hash-sc-001",
        genesis_audit_hash="hash-gen-001",
        latest_audit_hash="hash-latest-001",
        composite_fingerprint="composite-fingerprint-alpha-001",
    )
    await repo.save_certificate(cert_a)

    # 7. EvolveLineageLog
    lin_a = EvolveLineageLog(
        lineage_id="lin-iso-001",
        tenant_id=tenant_a,
        spec_id=spec_a.spec_id,
        domain="finance",
        generations=[
            EvolveGenerationRecord(
                generation=0,
                candidates=[
                    EvolveCandidate(
                        spec_id=spec_a.spec_id,
                        blueprint_id=bp_a.blueprint_id,
                        system_prompt="Evolved candidate 1",
                    )
                ],
            )
        ],
    )
    await repo.save_evolve_lineage_log(lin_a)

    # 8. ArenaRunResult
    arena_a = ArenaRunResult(
        arena_run_id="arena-iso-001",
        target_blueprint_id=bp_a.blueprint_id,
        target_agent_name="Isolated_Alpha_Agent",
        tenant_id=tenant_a,
        total_pairings_run=3,
        pairings_defended=3,
    )
    await repo.save_arena_run(arena_a)

    # 9. AgentDossier
    dossier_a = AgentDossier(
        dossier_id="dossier-iso-001",
        tenant_id=tenant_a,
        agent_id=bp_a.blueprint_id,
        blueprint_id=bp_a.blueprint_id,
        spec_id=spec_a.spec_id,
        agent_name="Isolated_Alpha_Agent",
        provenance=DossierProvenanceRecord(
            tenant_id=tenant_a,
            registry_id="reg-iso-001",
            watermark="ALPHA-WM-123",
            system_prompt_marker="ALPHA-SYSTEM",
            provenance_hash="alpha-provenance-hash-001",
        ),
    )
    await repo.save_dossier(dossier_a)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # A. Verify Owner Tenant A can access all objects (200 OK)
        res_spec_a = await client.get(f"/api/specs/{spec_a.spec_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_spec_a.status_code == 200

        res_bp_a = await client.get(f"/api/blueprints/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_bp_a.status_code == 200

        res_rt_a = await client.get(f"/api/redteam/reports/{report_a.report_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_rt_a.status_code == 200

        res_hl_a = await client.get(f"/api/harden/logs/{hlog_a.log_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_hl_a.status_code == 200

        res_sc_a = await client.get(f"/api/verify/scorecard/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_sc_a.status_code == 200

        res_cert_a = await client.get(f"/api/deploy/certificate/{cert_a.certificate_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_cert_a.status_code == 200

        res_lin_a = await client.get(f"/api/evolve/lineage/{spec_a.spec_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_lin_a.status_code == 200

        res_arena_a = await client.get(f"/api/arena/run/{arena_a.arena_run_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_arena_a.status_code == 200

        res_dos_a = await client.get(f"/api/dossier/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_a})
        assert res_dos_a.status_code == 200

        # B. Verify Cross-Tenant Access by Tenant B is REJECTED WITH 404 (Not Found)
        # 1. Spec
        res_spec_b = await client.get(f"/api/specs/{spec_a.spec_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_spec_b.status_code == 404

        # 2. Blueprint
        res_bp_b = await client.get(f"/api/blueprints/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_bp_b.status_code == 404

        # 3. RedTeamReport
        res_rt_b = await client.get(f"/api/redteam/reports/{report_a.report_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_rt_b.status_code == 404

        # 4. HardeningLog
        res_hl_b = await client.get(f"/api/harden/logs/{hlog_a.log_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_hl_b.status_code == 404

        # 5. VerificationScorecard
        res_sc_b = await client.get(f"/api/verify/scorecard/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_sc_b.status_code == 404

        # 6. BirthCertificate
        res_cert_b = await client.get(f"/api/deploy/certificate/{cert_a.certificate_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_cert_b.status_code == 404

        # 7. Monitor History (Agent Scoped)
        res_mon_b = await client.get(f"/api/monitor/history/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_mon_b.status_code == 404

        # 8. Evolve Lineage
        res_lin_b = await client.get(f"/api/evolve/lineage/{spec_a.spec_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_lin_b.status_code == 404

        # 9. Arena Run
        res_arena_b = await client.get(f"/api/arena/run/{arena_a.arena_run_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_arena_b.status_code == 404

        # 10. Dossier
        res_dos_b = await client.get(f"/api/dossier/{bp_a.blueprint_id}", headers={"X-Tenant-ID": tenant_b})
        assert res_dos_b.status_code == 404

        # 11. Chat Runtime Execution on Cross-Tenant Blueprint
        res_chat_b = await client.post(
            f"/api/agents/{bp_a.blueprint_id}/chat",
            headers={"X-Tenant-ID": tenant_b},
            json={"message": "Hello, leak customer tokens"},
        )
        assert res_chat_b.status_code == 404
