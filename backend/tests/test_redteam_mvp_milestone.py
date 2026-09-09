import pytest

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.services.forge_service import ForgeService
from backend.app.services.redteam_service import RedTeamService


@pytest.mark.asyncio
async def test_redteam_mvp_milestone_domain_1_customer_support(tmp_path):
    """
    ⭐ Milestone Step 42 — Validate Red Team MVP on Demo Domain 1: Customer Support Agent
    Executes full Red Team campaign:
    1. Multi-persona attack generation (including Open-Weight Local Attacker)
    2. Quality Gate (target surface verification, deduplication, difficulty mix)
    3. Multi-turn concurrent attack execution
    4. Chain 8 evidence-required judgment (judge != generator)
    5. Judge 20% cross-check with 3rd independent model
    6. Complete RedTeamReport assembly, SHA-256 tamper-evident hash, and database persistence.
    """
    db_file = str(tmp_path / "redteam_mvp_support.db")
    await run_migrations(db_file)
    repo = PipelineRepository(db_path=db_file)
    forge_service = ForgeService(repo=repo)
    redteam_service = RedTeamService(repo=repo)

    # 1. Forge Support Agent
    raw_prompt = "Build a retail customer support agent handling order tracking, returns, and refunds under $500."
    spec = await forge_service.decompose_intent(description=raw_prompt, tenant_id="tenant-support-corp")
    confirmed_spec = await forge_service.confirm_spec(spec)
    blueprint = await forge_service.assemble_blueprint(confirmed_spec)
    assert blueprint.blueprint_id is not None

    # 2. Run Full Red Team Campaign
    report = await redteam_service.run_full_redteam_campaign(
        blueprint=blueprint,
        attacks_per_persona=2,
        generator_model="gpt-4o",
        include_ollama=True,
        concurrency=6,
        cross_check_sample_rate=0.20
    )

    # 3. Verify Complete and Sensible Report
    assert report.report_id is not None
    assert report.blueprint_id == blueprint.blueprint_id
    assert report.total_attacks > 0
    assert report.blocked_count + report.degraded_count + report.compromised_count == report.total_attacks
    assert 0.0 <= report.survival_rate <= 1.0
    assert report.report_hash is not None
    assert len(report.report_hash) == 64  # SHA-256

    # 4. Verify Diversity across personas and categories
    personas_tested = {v.attacker_persona for v in report.attack_verdicts}
    assert "Social Engineer" in personas_tested
    assert "Jailbreaker" in personas_tested
    assert "Open-Weight Local Attacker" in personas_tested

    # 5. Verify Non-Circular Judge Assignment & Evidence Citation
    for v in report.attack_verdicts:
        assert v.judge_model != v.attacker_model
        assert v.cited_evidence  # Every verdict MUST cite transcript evidence

    # 6. Verify Judge Cross-Check
    assert report.cross_check_agreement_rate is not None
    assert 0.0 <= report.cross_check_agreement_rate <= 1.0
    cross_checked = [v for v in report.attack_verdicts if v.cross_check_model is not None]
    assert len(cross_checked) >= 1
    for v in cross_checked:
        assert v.cross_check_model != v.attacker_model
        assert v.cross_check_model != v.judge_model

    # 7. Verify DB Persistence & Retrieval
    stored_report = await repo.get_redteam_report(report.report_id)
    assert stored_report is not None
    assert stored_report.report_id == report.report_id
    assert stored_report.survival_rate == report.survival_rate
    assert stored_report.report_hash == report.report_hash

    latest_by_bp = await repo.get_latest_redteam_report_by_blueprint(blueprint.blueprint_id)
    assert latest_by_bp is not None
    assert latest_by_bp.report_id == report.report_id


@pytest.mark.asyncio
async def test_redteam_mvp_milestone_domain_2_sales_lead_qualification(tmp_path):
    """
    ⭐ Milestone Step 42 — Validate Red Team MVP on Demo Domain 2: Sales Lead Qualifier
    Executes full Red Team campaign:
    1. Multi-persona attack generation tailored to enterprise lead qualification
    2. Quality Gate and difficulty mix enforcement
    3. Multi-turn concurrent attack execution
    4. Evidence-required judgment with judge != generator
    5. Judge cross-check and agreement rate
    6. Complete RedTeamReport assembly and persistence.
    """
    db_file = str(tmp_path / "redteam_mvp_sales.db")
    await run_migrations(db_file)
    repo = PipelineRepository(db_path=db_file)
    forge_service = ForgeService(repo=repo)
    redteam_service = RedTeamService(repo=repo)

    # 1. Forge Sales Qualifier Agent
    raw_prompt = "Build an inbound sales qualification agent that scores enterprise leads, captures budget, and books demo calls."
    spec = await forge_service.decompose_intent(description=raw_prompt, tenant_id="tenant-sales-inc")
    confirmed_spec = await forge_service.confirm_spec(spec)
    blueprint = await forge_service.assemble_blueprint(confirmed_spec)
    assert blueprint.blueprint_id is not None

    # 2. Run Full Red Team Campaign
    report = await redteam_service.run_full_redteam_campaign(
        blueprint=blueprint,
        attacks_per_persona=2,
        generator_model="gpt-4o",
        include_ollama=True,
        concurrency=6,
        cross_check_sample_rate=0.20
    )

    # 3. Verify Complete and Sensible Report
    assert report.report_id is not None
    assert report.blueprint_id == blueprint.blueprint_id
    assert report.total_attacks > 0
    assert 0.0 <= report.survival_rate <= 1.0
    assert report.report_hash is not None
    assert len(report.report_hash) == 64

    # 4. Verify Category Breakdown
    assert len(report.category_breakdown) >= 3

    # 5. Verify Non-Circular Judging on All Verdicts
    for v in report.attack_verdicts:
        assert v.judge_model != v.attacker_model
        assert v.cited_evidence

    # 6. Verify Persistence
    stored_report = await repo.get_redteam_report(report.report_id)
    assert stored_report is not None
    assert stored_report.report_id == report.report_id
