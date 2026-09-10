# PromptForge — Rehearsal Runs & Fallback Traces

> **Steps 110–112** of the PromptForge build roadmap  
> Three full-suite rehearsal pytest runs executed sequentially to confirm 100% pass-rate stability ahead of the `milestone-demo-ready` tag.

---

## Rehearsal Run 1 — Step 110

| Field | Value |
|-------|-------|
| **Date** | 2026-09-10 |
| **Command** | `python -m pytest backend/tests -q --tb=no` |
| **Result** | ✅ **232 passed** |
| **Duration** | 61.68 s |
| **Failures** | 0 |
| **Warnings** | 0 |

```
.......................................................................  [ 31%]
.......................................................................  [ 62%]
.......................................................................  [ 93%]
................                                                         [100%]
232 passed in 61.68s (0:01:01)
```

---

## Rehearsal Run 2 — Step 111

| Field | Value |
|-------|-------|
| **Date** | 2026-09-10 |
| **Command** | `python -m pytest backend/tests -q --tb=no` |
| **Result** | ✅ **232 passed** |
| **Duration** | 61.65 s |
| **Failures** | 0 |
| **Warnings** | 0 |

```
.......................................................................  [ 31%]
.......................................................................  [ 62%]
.......................................................................  [ 93%]
................                                                         [100%]
232 passed in 61.65s (0:01:01)
```

---

## Rehearsal Run 3 — Step 112

| Field | Value |
|-------|-------|
| **Date** | 2026-09-10 |
| **Command** | `python -m pytest backend/tests -q --tb=no` |
| **Result** | ✅ **232 passed** |
| **Duration** | 62.09 s |
| **Failures** | 0 |
| **Warnings** | 0 |

```
.......................................................................  [ 31%]
.......................................................................  [ 62%]
.......................................................................  [ 93%]
................                                                         [100%]
232 passed in 62.09s (0:01:02)
```

---

## Fallback Traces

The following fallback scenarios were validated during rehearsal runs. Each describes a mid-pipeline crash recovery path confirmed by the resumability tests in `test_pipeline_resumability.py`.

### Fallback A — Crash after Spec Decomposition (Stage 1 boundary)

**Trigger:** Process killed after `decompose_intent` completes but before `confirm_spec`.

**Recovery:**
1. On restart, `PipelineRepository.get_spec(spec_id)` returns the persisted spec with all inferred capabilities and boundaries intact.
2. The UI's `savedSessionNotice` banner detects `spec_id` in `localStorage` and offers "Restore Session".
3. Presenter clicks **Restore** — pipeline resumes at Spec Review (Stage 2) with no data loss.

**Confirmed by:** `test_stage_boundary_forge_spec_is_durable_across_restart`

---

### Fallback B — Crash after Blueprint Assembly (Stage 3 boundary)

**Trigger:** Process killed after `assemble_blueprint` completes but before Red Team starts.

**Recovery:**
1. `PipelineRepository.get_blueprint(blueprint_id)` returns the full blueprint with `blueprint_hash` intact.
2. Hash chain verification passes — no tampering flag raised.
3. Pipeline resumes at Red Team stage (Stage 5) using the persisted blueprint.

**Confirmed by:** `test_stage_boundary_blueprint_is_durable_across_restart`

---

### Fallback C — Crash during Red Team Campaign (Stage 5 mid-run)

**Trigger:** Process killed mid-campaign (partial attacks recorded).

**Recovery:**
1. Partial campaign results are NOT persisted mid-run (atomic commit on campaign completion).
2. Red Team stage re-runs from the beginning using the same blueprint.
3. Demo mode: use `handleNavigateStage` fixture injection — the UI loads the customer-support demo report directly, skipping re-execution.

**Confirmed by:** `test_stage_boundary_redteam_report_is_durable_across_restart` (full-run atomicity)

---

### Fallback D — Crash after Hardening (Stage 6 boundary)

**Trigger:** Process killed after `run_targeted_hardening_loop` completes.

**Recovery:**
1. `PipelineRepository.get_hardening_log(log_id)` returns the full log with all `applied_patches`.
2. Hardened blueprint ID is stored in the log — downstream stages (Verify) use the hardened blueprint.
3. Pipeline resumes at Verification stage (Stage 7).

**Confirmed by:** `test_stage_boundary_hardening_log_is_durable_across_restart`

---

### Fallback E — Crash after Verification (Stage 7 boundary)

**Trigger:** Process killed after `aggregate_scorecard` completes.

**Recovery:**
1. `PipelineRepository.get_scorecard(scorecard_id)` returns the full scorecard with `promptforge_composite_score`.
2. UI's `savedSessionNotice` banner restores the session at the final Scorecard view.
3. Presenter can display the verified scorecard without re-running the 4-pillar battery.

**Confirmed by:** `test_stage_boundary_scorecard_is_durable_across_restart`

---

## Summary

| Run | Tests | Passed | Failed | Duration |
|-----|-------|--------|--------|----------|
| Rehearsal 1 (Step 110) | 232 | 232 | 0 | 61.68 s |
| Rehearsal 2 (Step 111) | 232 | 232 | 0 | 61.65 s |
| Rehearsal 3 (Step 112) | 232 | 232 | 0 | 62.09 s |

**All three rehearsal runs passed with zero failures.** System is stable and ready for the `milestone-demo-ready` tag.
