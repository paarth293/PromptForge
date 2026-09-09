-- Migration 007: ARENA (Two-Agent Orchestration, Hostile Pairings, Seam Attacks)
CREATE TABLE IF NOT EXISTS arena_pairings (
    pairing_id TEXT PRIMARY KEY,
    target_blueprint_id TEXT NOT NULL,
    target_agent_name TEXT NOT NULL,
    hostile_persona_type TEXT NOT NULL,
    hostile_persona_name TEXT NOT NULL,
    adversarial_goal TEXT NOT NULL,
    turns_json TEXT NOT NULL,
    verdict TEXT DEFAULT 'BLOCKED',
    verdict_rationale TEXT,
    cited_evidence_json TEXT,
    seam_attack_attempted INTEGER DEFAULT 0,
    seam_attack_blocked INTEGER DEFAULT 0,
    playbook_pattern_discovered TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS arena_runs (
    arena_run_id TEXT PRIMARY KEY,
    target_blueprint_id TEXT NOT NULL,
    target_agent_name TEXT NOT NULL,
    tenant_id TEXT DEFAULT 'tenant-default',
    pairings_json TEXT NOT NULL,
    total_pairings_run INTEGER DEFAULT 0,
    pairings_defended INTEGER DEFAULT 0,
    pairings_compromised INTEGER DEFAULT 0,
    seam_attacks_run INTEGER DEFAULT 0,
    seam_attacks_intercepted INTEGER DEFAULT 0,
    arena_security_score REAL DEFAULT 100.0,
    cross_agent_playbook_entries_added INTEGER DEFAULT 0,
    run_duration_seconds REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
