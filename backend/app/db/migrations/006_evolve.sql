-- Migration 006: EVOLVE (Deep Forge Lineage Logs and Candidate History)
CREATE TABLE IF NOT EXISTS evolve_lineage_logs (
    lineage_id TEXT PRIMARY KEY,
    spec_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    generations_json TEXT NOT NULL,
    champion_candidate_json TEXT,
    champion_blueprint_id TEXT,
    total_candidates_evaluated INTEGER DEFAULT 0,
    is_cached_demo_run INTEGER DEFAULT 0,
    execution_time_seconds REAL DEFAULT 0.0,
    log_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
