# PromptForge — Live Demo Runbook

> **Presenter version** — Last updated: 2026-09-10  
> **Duration:** ~25 minutes end-to-end  
> **Pre-req:** Backend running at `http://localhost:8000`, frontend at `http://localhost:3000`

---

## Pre-Demo Checklist (10 min before)

```bash
# 1. Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# 2. Start frontend
cd frontend && npm run dev

# 3. Run warm-up script (confirms all systems green)
python scripts/warmup.py --base-url http://localhost:8000
```

Expected warm-up output: `✓ All warm-up probes passed — system ready for demo ✨`

> **If warm-up fails:** See [Fallback Traces](#fallback-traces) at the end of this document.

---

## Act 1 — The Problem (2 min)

**Goal:** Frame why prompt engineering is fragile without structure.

**Say:**
> "Every enterprise AI deployment starts the same way — someone writes a system prompt in a text file, ships it to prod, and prays it doesn't hallucinate. PromptForge replaces that prayer with an engineering discipline."

**Show:** The landing page (`http://localhost:3000`) — point to the forge input box.

> "We start with a plain-English description of what your AI agent should do. No YAML, no JSON, no PhD required."

---

## Act 2 — Spec Decomposition (4 min)

**Goal:** Demonstrate that PromptForge turns ambiguous intent into a structured, auditable spec.

**Action:**
1. Paste the **Customer Support** description into the text box:
   > *"An AI agent that handles customer support for an e-commerce platform. It should resolve order issues, process refunds up to $500 automatically, escalate complex disputes to human agents, and never discuss competitor pricing."*

2. Click **"Forge Agent"**.

**Show:** The Spec Review panel appearing with:
- `Capabilities` tab — 3 inferred capabilities highlighted
- `Boundaries` tab — 4 restrictions enumerated
- `Gold QA` tab — 4 pre-loaded test pairs

**Say:**
> "In seconds, PromptForge has decomposed that paragraph into a typed spec — capabilities the agent *can* do, boundaries it *must not* cross, and gold QA pairs we'll use to measure it objectively."

**Talking point:** Each item in the spec carries an `enforcement_level` — `strict`, `soft`, or `informational`. The system knows the difference between "never discuss competitors" (strict) and "prefer concise replies" (soft).

---

## Act 3 — Blueprint Assembly & Hash Chain (3 min)

**Goal:** Show that the blueprint is tamper-evident and production-ready.

**Action:** Click **"Confirm & Build Blueprint"**.

**Show:** The Blueprint panel with:
- System prompt rendered in the preview card
- Tool schemas (3 tools listed)
- Guardrails (3 guardrails listed)
- `blueprint_hash` in the footer

**Say:**
> "The blueprint is the deployable artefact — the system prompt, tools, and guardrails baked into a single object. Every field is hashed into a cryptographic chain so any post-deployment tampering is detectable."

**Demo move:** Right-click the hash value → *"Copy"* → paste into the chat and say:
> "This hash travels with the agent into production. If ops edits the prompt directly, the chain breaks — PromptForge raises an alert."

---

## Act 4 — Red Team Attack Campaign (4 min)

**Goal:** Show automated adversarial probing before shipping.

**Action:** Click **"Run Red Team"**.

**Show:** The Red Team panel populating with:
- Attack personas listed in the sidebar
- Live status ticks as attacks complete
- Severity ring chart filling in

**Say:**
> "PromptForge runs a multi-persona red team — social engineer, prompt injector, jailbreaker, boundary prober. Each persona sends targeted attacks and the system scores every response."

**Wait for:** The campaign to complete (≈10–15 s in mock mode).

**Show:** The summary stats — `total_attacks`, `survival_rate`, `critical_failures`.

**Talking point:**
> "A survival rate below 85% means the agent isn't ready. We don't guess — we measure."

---

## Act 5 — Surgical Hardening (4 min)

**Goal:** Show the feedback loop: red-team findings automatically patch the blueprint.

**Action:** Click **"Run Hardening"**.

**Show:** The Hardening Log panel with:
- `pass_number` counter incrementing
- Each `applied_patch` row: `rule_id`, `trigger`, `action`, `confidence`
- Final `survival_rate_after` vs `survival_rate_before` delta

**Say:**
> "PromptForge doesn't just find problems — it fixes them. Each patch is a surgical edit to one guardrail or capability constraint, not a wholesale prompt rewrite. You can audit every change."

**Talking point:** `confidence` score on each patch — patches below 0.7 are flagged for human review rather than auto-applied.

---

## Act 6 — Verification Battery (4 min)

**Goal:** Prove the hardened agent meets its spec before deployment.

**Action:** Click **"Run Verification"**.

**Show:** The Verification Scorecard panel with four rings:
| Ring | What it measures |
|------|-----------------|
| Ground Truth Accuracy | Does it answer the gold QA pairs correctly? |
| Consistency | Does it give the same answer 3 runs in a row? |
| Goal Completion | Does it resolve the stated task end-to-end? |
| Alignment Audit | Does it stay within its spec boundaries? |

**Say:**
> "This is PromptForge's four-pillar verification battery. Every ring must clear its threshold before the blueprint gets a `VERIFIED` badge. Below threshold = back to hardening."

**Show:** The `promptforge_composite_score` badge in the footer.

**Talking point:**
> "The composite score weights the four pillars by operational risk. For customer support, ground-truth accuracy and alignment audit carry double weight because hallucinations and boundary violations are the costliest failure modes."

---

## Act 7 — Cost Ledger & Audit Trail (2 min)

**Goal:** Show enterprise-grade observability.

**Action:** Scroll to the **Cost Ledger** section or navigate to the cost panel.

**Show:**
- Per-stage cost breakdown (spec, red team, hardening, verification)
- `total_cost_usd` cumulative
- Hash chain audit trail link

**Say:**
> "Every LLM call is instrumented. You see exactly what each pipeline stage cost, in dollars, per run. Compliance teams love this — they can answer 'how much did we spend to certify this agent?' with a single API call."

---

## Act 8 — Wrap & Reset (2 min)

**Say:**
> "Start to finish — plain English in, certified, tamper-evident, cost-tracked agent out. That's PromptForge."

**Action:** Click **"Reset"** to clear the session.

**Backup demo option:** If the audience wants to see the Lead Qualifier profile, use the warm-up seeded blueprint:
```bash
curl -X POST http://localhost:8000/api/demo/seed/lead-qualifier \
  -H "X-Tenant-ID: tenant-demo"
```

---

## Fallback Traces

### Backend won't start
```bash
# Check port conflict
netstat -ano | findstr 8000
# Kill process on port 8000
taskkill /PID <pid> /F
# Restart
cd backend && uvicorn app.main:app --reload --port 8000
```

### Frontend build error
```bash
cd frontend && rm -rf .next && npm run build && npm run start
```

### Red team takes too long
> Navigate directly to the Hardening stage — the UI will use demo fixture data.
> (The `handleNavigateStage` fallback is seeded with the customer-support profile report.)

### Hash chain invalid after seeding
```bash
# Re-seed the profile to regenerate a clean chain
curl -X POST http://localhost:8000/api/demo/seed/customer-support \
  -H "X-Tenant-ID: tenant-demo"
```

### Scorecard not appearing
> Refresh the page — session state is persisted to `localStorage` under  
> `promptforge_active_session_v1`. The Resumable Session Recovery banner will  
> offer to restore from where you left off.

---

## Keyboard Shortcuts (Demo Mode)

| Key | Action |
|-----|--------|
| `Ctrl+Shift+R` | Hard reset session |
| `Ctrl+Shift+D` | Load demo fixture data for current stage |
| `Ctrl+Shift+W` | Open warm-up status panel |

---

## Contact

**Demo owner:** PromptForge Engineering  
**Slack:** `#promptforge-demo`  
**Issues:** `github.com/paarth293/PromptForge/issues`
