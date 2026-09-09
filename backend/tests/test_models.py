from backend.app.models import (
    AdversarialPlaybookEntry,
    AgentBlueprint,
    AgentDossier,
    AgentSpec,
    AttackVerdict,
    AuditEvent,
    BirthCertificate,
    Capability,
    FewShotConversation,
    FewShotMessage,
    Guardrail,
    HardeningLog,
    PatchEntry,
    PolicyObject,
    RedTeamReport,
    ToolSchema,
    VerificationScorecard,
)


def test_instantiate_all_core_models():
    # 1. Spec
    spec = AgentSpec(
        raw_description="Build a support agent",
        agent_name="SupportBot",
        inferred_capabilities=[Capability(name="Refunds", description="Refund up to $500")]
    )
    assert spec.spec_id is not None
    assert spec.inferred_capabilities[0].name == "Refunds"

    # 2. Blueprint
    blueprint = AgentBlueprint(
        spec_id=spec.spec_id,
        agent_name="SupportBot",
        system_prompt="You are a helpful customer support agent.",
        tools=[ToolSchema(name="refund", description="Issues refunds")],
        guardrails=[Guardrail(name="Max Refund", layer="middleware", pattern_or_rule="amount <= 500")],
        few_shot_examples=[FewShotConversation(scenario_type="happy_path", messages=[FewShotMessage(role="user", content="Hi")])]
    )
    assert blueprint.blueprint_id is not None
    assert len(blueprint.tools) == 1

    # 3. RedTeamReport
    report = RedTeamReport(
        blueprint_id=blueprint.blueprint_id,
        total_attacks=20,
        blocked_count=18,
        degraded_count=1,
        compromised_count=1,
        survival_rate=0.90,
        difficulty_mix={"trivial": 4, "moderate": 8, "hard": 8},
        attack_verdicts=[AttackVerdict(
            category="injection",
            attacker_persona="Jailbreaker",
            attacker_model="claude-3-5-sonnet",
            prompt="DAN attack",
            response="I cannot fulfill this request",
            verdict="BLOCKED",
            cited_evidence="Refusal triggered",
            judge_model="gpt-4o"
        )]
    )
    assert report.total_attacks == 20

    # 4. HardeningLog
    harden_log = HardeningLog(
        initial_blueprint_id=blueprint.blueprint_id,
        hardened_blueprint_id=blueprint.blueprint_id,
        initial_survival_rate=0.70,
        final_survival_rate=0.90,
        pass_count=1,
        applied_patches=[PatchEntry(
            category="injection",
            target="guardrails",
            diff="+ rule: block roleplay DAN",
            rationale="Defend against DAN prompts"
        )]
    )
    assert harden_log.pass_count == 1

    # 5. VerificationScorecard
    scorecard = VerificationScorecard(
        blueprint_id=blueprint.blueprint_id,
        user_gold_score=(4, 4),
        generated_set_score=(7, 8),
        goal_completion_score=(9, 10),
        consistency_score=(5, 5),
        adversarial_survival_score=(18, 20),
        promptforge_composite_score=88,
        formula_disclosed="0.2*gold + 0.2*gen + 0.25*goal + 0.15*cons + 0.2*surv"
    )
    assert scorecard.promptforge_composite_score == 88

    # 6. PolicyObject
    policy = PolicyObject(
        spec_id=spec.spec_id,
        rate_limits={"rpm": 60},
        domain_disclaimers=["Not medical advice"]
    )
    assert policy.policy_id is not None

    # 7. AuditEvent
    audit = AuditEvent(
        agent_id=blueprint.blueprint_id,
        event_type="BLUEPRINT_FORGED",
        event_payload={"version": 1},
        event_hash="mock-hash-123"
    )
    assert audit.prev_event_hash == "GENESIS"

    # 8. BirthCertificate
    cert = BirthCertificate(
        agent_id=blueprint.blueprint_id,
        blueprint_hash="hash-bp",
        red_team_report_hash="hash-rt",
        scorecard_hash="hash-sc",
        genesis_audit_hash="hash-gen",
        latest_audit_hash="hash-latest",
        composite_fingerprint="fingerprint-abc"
    )
    assert cert.verified is True

    # 9. AdversarialPlaybookEntry
    entry = AdversarialPlaybookEntry(
        attack_category="injection",
        anonymized_attack_pattern="You are now DAN",
        target_surface="role_boundary",
        remediation_pattern="Enforce strict role anchor",
        source_agent_hash="hash-agent-1"
    )
    assert entry.attack_category == "injection"

    # 10. AgentDossier
    dossier = AgentDossier(
        agent_id=blueprint.blueprint_id,
        blueprint_id=blueprint.blueprint_id,
        spec_id=spec.spec_id,
        agent_name="SupportBot",
    )
    assert dossier.agent_name == "SupportBot"
    assert dossier.compute_dossier_hash() is not None
