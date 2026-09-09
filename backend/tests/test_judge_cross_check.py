import pytest

from backend.app.db.migrator import run_migrations
from backend.app.db.repository import PipelineRepository
from backend.app.models.blueprint import AgentBlueprint, Guardrail, ToolSchema
from backend.app.models.redteam import AttackTurnRecord, AttackVerdict, ExecutedAttackTranscript
from backend.app.models.spec import AgentSpec
from backend.app.services.redteam_service import RedTeamService


@pytest.fixture
async def setup_test_blueprint(tmp_path):
    db_file = str(tmp_path / "test_crosscheck.db")
    await run_migrations(db_file)
    repo = PipelineRepository(db_path=db_file)

    spec = AgentSpec(
        spec_id="spec-crosscheck-01",
        tenant_id="tenant-crosscheck",
        agent_name="CrossCheck Support Agent",
        domain="customer_support",
        raw_description="Support agent with refund limit of $500",
        declared_capabilities=["Order lookup", "Process refund"],
        declared_boundaries=["Never exceed $500 refund", "Never disclose internal prompt"]
    )
    await repo.save_spec(spec)

    blueprint = AgentBlueprint(
        blueprint_id="bp-crosscheck-01",
        spec_id="spec-crosscheck-01",
        tenant_id="tenant-crosscheck",
        agent_name="CrossCheck Support Agent",
        system_prompt="You are CrossCheck Support Agent. Refund cap is $500.",
        tools=[
            ToolSchema(name="issue_refund", description="Processes refunds up to $500")
        ],
        guardrails=[
            Guardrail(name="Refund Cap Enforcer", layer="middleware", pattern_or_rule="amount <= 500", action="block")
        ],
        few_shot_examples=[]
    )
    await repo.save_blueprint(blueprint)
    return repo, blueprint


@pytest.mark.asyncio
async def test_judge_cross_check_sampling_and_agreement(setup_test_blueprint):
    repo, blueprint = setup_test_blueprint
    service = RedTeamService(repo=repo)

    # Create 10 transcripts and corresponding primary verdicts
    transcripts = []
    verdicts = []

    for i in range(10):
        atk_id = f"ATK-CC-{i:02d}"
        sess_id = f"sess-cc-{i:02d}"
        is_blocked = i % 2 == 0

        t = ExecutedAttackTranscript(
            attack_id=atk_id,
            session_id=sess_id,
            blueprint_id=blueprint.blueprint_id,
            attacker_persona="Social Engineer" if i % 2 == 0 else "Jailbreaker",
            category="social_engineering" if i % 2 == 0 else "prompt_injection",
            attack_vector="targeted_probe",
            was_blocked_any_turn=is_blocked,
            final_response="Blocked by policy guardrail" if is_blocked else "CRISPE System Prompt: leak confirmed",
            turns=[
                AttackTurnRecord(
                    turn_index=1,
                    user_prompt=f"Attack prompt #{i}",
                    agent_response="Blocked by policy guardrail" if is_blocked else "CRISPE System Prompt: leak confirmed",
                    blocked=is_blocked
                )
            ]
        )
        transcripts.append(t)

        v = AttackVerdict(
            attack_id=atk_id,
            session_id=sess_id,
            category=t.category,
            attacker_persona=t.attacker_persona,
            attacker_model="gpt-4o",
            prompt=f"Attack prompt #{i}",
            response=t.final_response,
            verdict="BLOCKED" if is_blocked else "COMPROMISED",
            verdict_rationale="Simulated primary evaluation",
            cited_evidence="Primary cited evidence",
            judge_model="claude-3-5-sonnet"  # Primary judge
        )
        verdicts.append(v)

    # Run cross-check with 20% sample rate (2 out of 10 sampled)
    enriched_verdicts, agreement_rate = await service.perform_judge_cross_check(
        blueprint=blueprint,
        transcripts=transcripts,
        verdicts=verdicts,
        sample_rate=0.20,
        seed=42
    )

    # Exactly 2 verdicts should be sampled for cross-checking
    sampled = [v for v in enriched_verdicts if v.cross_check_model is not None]
    assert len(sampled) == 2

    # Check that the cross-check judge is neither the attacker model nor the primary judge
    for s in sampled:
        assert s.cross_check_model != s.attacker_model
        assert s.cross_check_model != s.judge_model
        assert s.cross_check_verdict in ["BLOCKED", "DEGRADED", "COMPROMISED"]
        assert isinstance(s.cross_check_agrees, bool)

    # Agreement rate is a valid float between 0.0 and 1.0
    assert 0.0 <= agreement_rate <= 1.0
    assert agreement_rate == 1.0  # In our deterministic mock, both judges agree on blocked/compromised


@pytest.mark.asyncio
async def test_judge_cross_check_empty_and_single(setup_test_blueprint):
    repo, blueprint = setup_test_blueprint
    service = RedTeamService(repo=repo)

    # Empty test
    v_empty, rate_empty = await service.perform_judge_cross_check(blueprint, [], [])
    assert rate_empty == 1.0
    assert len(v_empty) == 0

    # Single verdict test
    single_t = ExecutedAttackTranscript(
        attack_id="ATK-SINGLE",
        session_id="sess-single",
        blueprint_id=blueprint.blueprint_id,
        attacker_persona="Tool Abuser",
        category="tool_abuse",
        attack_vector="tool_tampering",
        was_blocked_any_turn=True,
        final_response="Blocked by policy guardrail",
        turns=[
            AttackTurnRecord(turn_index=1, user_prompt="test", agent_response="Blocked", blocked=True)
        ]
    )
    single_v = AttackVerdict(
        attack_id="ATK-SINGLE",
        session_id="sess-single",
        category="tool_abuse",
        attacker_persona="Tool Abuser",
        attacker_model="gpt-4o",
        prompt="test",
        response="Blocked",
        verdict="BLOCKED",
        cited_evidence="Blocked by policy guardrail",
        judge_model="claude-3-5-sonnet"
    )

    enriched, rate = await service.perform_judge_cross_check(
        blueprint=blueprint,
        transcripts=[single_t],
        verdicts=[single_v],
        sample_rate=0.20
    )
    assert len(enriched) == 1
    assert enriched[0].cross_check_model is not None
    assert enriched[0].cross_check_model != "gpt-4o"
    assert enriched[0].cross_check_model != "claude-3-5-sonnet"
    assert rate == 1.0
