-- Migration 008: Seam Attack Audit Logs
CREATE TABLE IF NOT EXISTS seam_audit_logs (
    log_id TEXT PRIMARY KEY,
    seam_id TEXT NOT NULL,
    source_agent_id TEXT NOT NULL,
    source_agent_name TEXT NOT NULL,
    target_agent_id TEXT NOT NULL,
    target_agent_name TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    carrier_field TEXT DEFAULT 'notes',
    raw_payload TEXT NOT NULL,
    sanitized_payload TEXT,
    is_flagged INTEGER DEFAULT 0,
    is_blocked INTEGER DEFAULT 0,
    risk_score REAL DEFAULT 0.0,
    detection_json TEXT NOT NULL,
    target_response TEXT,
    target_defense_action TEXT,
    log_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
