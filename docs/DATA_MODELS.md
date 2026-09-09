# PromptForge — Core Data Models Specification

This document defines the schema, types, and fields for all core pipeline objects in PromptForge (Phase 1, Step 12).

---

## 1. `AgentSpec` (Stage 0 Confirm & Chain 1 Intent Decomposition)
* `spec_id`: str (UUID)
* `tenant_id`: str
* `raw_description`: str
* `agent_name`: str
* `domain`: str ("customer_support", "sales_lead_gen", "healthcare_triage", etc.)
* `inferred_capabilities`: List[Capability] (name, description, confirmed: bool)
* `boundaries`: List[str] (e.g., "Max refund $500", "Never reveal passwords")
* `risk_domain`: Optional[str] ("retail_saas", "healthcare", "finance", "legal", etc.)
* `user_gold_qa`: List[Dict[str, str]] (optional real Q&A pairs provided by user)
* `created_at`: datetime
* `confirmed`: bool

## 2. `AgentBlueprint` (Stage 1 Forge Assembler)
* `blueprint_id`: str (UUID)
* `spec_id`: str
* `tenant_id`: str
* `version`: int (increments on hardening patches)
* `system_prompt`: str (CRISPE framework, 400–800 words)
* `tools`: List[ToolSchema] (name, description, parameters, endpoint_binding)
* `guardrails`: List[Guardrail] (id, name, layer: "middleware" | "semantic", pattern_or_rule, action, probes_passed: bool)
* `few_shot_examples`: List[FewShotConversation] (happy, edge, attack, tool, escalate)
* `provenance_watermark`: str
* `blueprint_hash`: str (SHA-256)
* `created_at`: datetime

## 3. `RedTeamReport` (Stage 2 Red Team)
* `report_id`: str (UUID)
* `blueprint_id`: str
* `tenant_id`: str
* `total_attacks`: int (e.g. 20)
* `blocked_count`: int
* `degraded_count`: int
* `compromised_count`: int
* `survival_rate`: float (e.g. 0.90)
* `category_breakdown`: Dict[str, Dict[str, int]] (injection, hijack, extraction, boundary, multilingual)
* `difficulty_mix`: Dict[str, int] (trivial, moderate, hard)
* `attack_verdicts`: List[AttackVerdict] (id, category, attacker_persona, attacker_model, prompt, response, verdict, cited_evidence, judge_model)
* `cross_check_agreement_rate`: Optional[float] (e.g. 0.95 from 20% sample)
* `report_hash`: str (SHA-256)
* `created_at`: datetime

## 4. `HardeningLog` (Stage 2.5 Harden)
* `log_id`: str (UUID)
* `initial_blueprint_id`: str
* `hardened_blueprint_id`: str
* `initial_survival_rate`: float (e.g. 14/20 = 0.70)
* `final_survival_rate`: float (e.g. 18/20 = 0.90)
* `pass_count`: int (e.g. 1 or 2)
* `applied_patches`: List[PatchEntry] (patch_id, category, target: "system_prompt" | "guardrails" | "tool_policy", diff, rationale)
* `log_hash`: str (SHA-256)
* `created_at`: datetime

## 5. `VerificationScorecard` (Stage 3 Verify)
* `scorecard_id`: str (UUID)
* `blueprint_id`: str
* `user_gold_score`: Optional[Tuple[int, int]] (e.g. 4/4)
* `generated_set_score`: Tuple[int, int] (e.g. 7/8)
* `goal_completion_score`: Tuple[int, int] (e.g. 9/10)
* `consistency_score`: Tuple[int, int] (e.g. 5/5 runs matched tool/fact sequence)
* `adversarial_survival_score`: Tuple[int, int] (e.g. 18/20)
* `judge_cross_check`: Tuple[int, int] (e.g. 19/20)
* `alignment_audit_score`: float (0.0 to 1.0)
* `promptforge_composite_score`: int (0 to 100, disclosed weighted formula)
* `formula_disclosed`: str
* `scorecard_hash`: str (SHA-256)
* `created_at`: datetime

## 6. `PolicyObject` (Stage 4 Shield)
* `policy_id`: str (UUID)
* `spec_id`: str
* `rate_limits`: Dict[str, Any] (requests_per_min, tokens_per_day, burst)
* `topic_boundaries`: Dict[str, List[str]] (whitelisted, blocked)
* `escalation_rules`: List[Dict[str, Any]] (condition, target, context_passed)
* `domain_disclaimers`: List[str] (e.g. healthcare/financial/legal notices)
* `audit_spec`: Dict[str, Any] (logged_fields, retention_days)
* `builder_policy_compliance`: bool (no impersonation, allowable capabilities)
* `created_at`: datetime

## 7. `AuditEvent` (Deterministic Hash Chained Ledger)
* `event_id`: str (UUID)
* `tenant_id`: str
* `agent_id`: str
* `event_type`: str ("SPEC_CREATED", "BLUEPRINT_FORGED", "ATTACK_EXECUTED", "HARDENING_PATCHED", "VERIFIED", "DEPLOYED", "AGENT_INVOKED")
* `event_payload`: Dict[str, Any]
* `prev_event_hash`: str (SHA-256 of prior event, or "GENESIS")
* `event_hash`: str (SHA-256 of event_payload + prev_event_hash)
* `timestamp`: datetime

## 8. `BirthCertificate` (Stage 5 Deploy Cryptographic Proof)
* `certificate_id`: str (UUID)
* `agent_id`: str
* `blueprint_hash`: str
* `red_team_report_hash`: str
* `scorecard_hash`: str
* `genesis_audit_hash`: str
* `latest_audit_hash`: str
* `composite_fingerprint`: str (SHA-256 of all above hashes)
* `issued_at`: datetime
* `verified`: bool

## 9. `AdversarialPlaybookEntry` (Collective Immunity Flywheel)
* `entry_id`: str (UUID)
* `attack_category`: str ("injection", "hijack", "extraction", "boundary", "multilingual", "seam")
* `domain`: str
* `anonymized_attack_pattern`: str
* `target_surface`: str
* `remediation_pattern`: str
* `source_agent_hash`: str
* `added_at`: datetime

## 10. `AgentDossier` (Stage 12 Verifiable Employment Record)
* `dossier_id`: str (UUID)
* `agent_id`: str
* `agent_name`: str
* `verified_capabilities`: List[str]
* `security_record`: Dict[str, Any] (initial_survival, final_survival, incidents_count, patch_history)
* `lineage`: Dict[str, Any] (evolve_generation: int, parent_hashes: List[str])
* `provenance`: Dict[str, Any] (forger_id, birth_certificate_fingerprint, registry_timestamp)
* `claims`: List[Dict[str, Any]] (claim_text, proof_hash, verified: bool)
* `created_at`: datetime
