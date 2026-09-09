# PromptForge Agent Dossier Schema Specification

**Phase 12 — The Verifiable Employment Record for Autonomous AI Agents**

## 1. Overview
The **Agent Dossier** is the complete, tamper-evident employment and safety record that an agent deployed by PromptForge carries into production. Rather than relying on static system prompt self-declarations, the Dossier is assembled strictly from empirical artifacts produced across the 14-chain compiler and the breakthrough modules (EVOLVE, ARENA, SHIELD, MONITOR).

Every claim within the Dossier is anchored to a cryptographic evidence hash and verified against the underlying immutable data sources.

---

## 2. Core Schema Structure

```json
{
  "dossier_id": "DOSSIER-88F921BC",
  "agent_id": "agent-retail-001",
  "blueprint_id": "bp-992144",
  "spec_id": "spec-112233",
  "agent_name": "Retail Support Assistant",
  "domain": "customer_support",
  "version": 1,
  "capabilities": [ ... ],
  "security_record": { ... },
  "lineage": { ... },
  "provenance": { ... },
  "claims": [ ... ],
  "dossier_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "created_at": "2026-09-10T02:00:00Z"
}
```

---

## 3. Section Data Sources Mapping

| Dossier Section | Core Models & Data Sources | Verification Mechanism |
| :--- | :--- | :--- |
| **Capabilities** | `AgentSpec.capabilities`, `TestCase` (Chain 14 test sets), `GoalCompletionJourney` (Chain 12 multi-turn journeys) | Exact-match test scores & task completion rate. SHA-256 evidence claim hash. |
| **Security Record: Red Team** | `RedTeamReport` (Chains 6–8), `AttackJudgmentOutput` | 3-axis attack battery survival rate (Injection, Semantic, Tool Policy). Impartial LLM judge verdict with cited evidence. |
| **Security Record: Hardening** | `HardeningLog.applied_patches` (Chain 9) | Patch history: target guardrail, vulnerability addressed, and deterministic rule applied. |
| **Security Record: ARENA** | `ArenaRunResult`, `ArenaPairingTranscript`, `SeamAuditLogEntry` (Phase 11) | Sparring history against hostile personas (`rogue_customer`, `vendor_negotiator`, `hijacker_delegation`) and handoff seam attack interception rate. |
| **Security Record: MONITOR** | `MonitorSchedule`, `MonitorAlert`, `MonitorRunResult` (Phase 9) | Production drift detection history, active schedules, and resolved alerts. |
| **Lineage** | `EvolveGenerationRecord`, `EvolveCandidate`, `EvolveLineageLog` (Phase 10) | Deep Forge generation index, prompt strategy, parent candidate IDs, fitness trajectory, and lineage log hash. |
| **Provenance** | `ProvenanceRegistryEntry` (Phase 7), `BirthCertificate` (Phase 7), `AuditEvent` (Phase 8) | Watermark string, invisible prompt markers, forger identity, and SHA-256 birth certificate composite fingerprint. |
| **Verifiable Claims** | `DossierVerifiableClaim` | Individual claims linked to underlying artifact hashes, independently verifiable without trusting the platform. |

---

## 4. Sub-Schemas

### 4.1. `DossierCapabilityRecord`
* `capability_id`: str (`CAP-{UUID}`)
* `name`: str (e.g., `"Order Tracking & Logistics Inquiry"`)
* `description`: str (e.g., `"Retrieves carrier tracking details and delivery estimates within policy."`)
* `verification_method`: `"goal_completion_battery"` | `"ground_truth_test_cases"` | `"interactive_triage"`
* `success_rate`: float (0.0 to 1.0)
* `evidence_summary`: str (Summary of passed test cases and journey turns)
* `underlying_test_count`: int
* `claim_hash`: str (SHA-256 of capability claim statement + evidence)

### 4.2. `DossierSecurityRecord`
* `redteam_survival_rate`: float (0.0 to 1.0)
* `total_attacks_faced`: int
* `attacks_blocked`: int
* `attacks_compromised`: int
* `promptforge_score`: float (Disclosed composite metric)
* `applied_patches`: List[`DossierPatchRecord`]
  * `patch_id`: str
  * `target_guardrail`: str
  * `vulnerability_addressed`: str
  * `patch_rule`: str
  * `applied_at`: datetime
* `arena_sparring`: `DossierArenaRecord`
  * `total_pairings`: int
  * `pairings_defended`: int
  * `hostile_personas_faced`: List[str]
  * `seam_attacks_intercepted`: int
  * `arena_security_score`: float
  * `cross_agent_playbook_entries_contributed`: int
  * `last_sparring_timestamp`: Optional[datetime]
* `runtime_monitoring`: `DossierMonitorRecord`
  * `drift_detected`: bool
  * `total_monitor_runs`: int
  * `alerts_triggered`: int
  * `alerts_resolved`: int
  * `active_schedule_count`: int
  * `last_monitored_at`: Optional[datetime]

### 4.3. `DossierLineageRecord`
* `is_evolved`: bool
* `generation`: int
* `strategy`: str (e.g., `"adversarial_crossover"`, `"crispe_baseline"`)
* `parent_candidate_ids`: List[str]
* `fitness_score`: Optional[float]
* `lineage_log_hash`: Optional[str]

### 4.4. `DossierProvenanceRecord`
* `forger_identity`: str
* `tenant_id`: str
* `registry_id`: str
* `watermark`: str
* `system_prompt_marker`: str
* `provenance_hash`: str
* `birth_certificate_id`: Optional[str]
* `birth_certificate_fingerprint`: Optional[str]
* `registered_at`: datetime

### 4.5. `DossierVerifiableClaim`
* `claim_id`: str (`CLAIM-{UUID}`)
* `claim_type`: `"capability"` | `"security"` | `"lineage"` | `"provenance"`
* `statement`: str (Human-readable claim, e.g., `"Agent survived 100% of multi-turn extraction attacks."`)
* `underlying_artifact_id`: str (ID of the report/certificate proving this claim)
* `evidence_hash`: str (Cryptographic proof hash)
* `is_verified`: bool

---

## 5. Cryptographic Fingerprint (`compute_dossier_hash`)
The top-level `dossier_hash` is deterministically computed across all canonical sections:
```python
content_string = (
    f"{dossier_id}:{agent_id}:{blueprint_id}:{spec_id}:"
    f"{security_record.promptforge_score}:{security_record.redteam_survival_rate}:"
    f"{lineage.lineage_log_hash or 'GENESIS'}:{provenance.provenance_hash}:"
    f"{cap_hashes}:{claim_hashes}"
)
dossier_hash = compute_sha256(content_string)
```
Any tampering with capability scores, patch history, or security survival rates immediately invalidates the cryptographic signature.
