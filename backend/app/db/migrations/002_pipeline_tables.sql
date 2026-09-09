-- Migration 002: Pipeline Objects Storage
CREATE TABLE IF NOT EXISTS specs (
    spec_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    domain TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blueprints (
    blueprint_id TEXT PRIMARY KEY,
    spec_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    blueprint_hash TEXT,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(spec_id) REFERENCES specs(spec_id)
);

CREATE TABLE IF NOT EXISTS redteam_reports (
    report_id TEXT PRIMARY KEY,
    blueprint_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    survival_rate REAL NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(blueprint_id) REFERENCES blueprints(blueprint_id)
);

CREATE TABLE IF NOT EXISTS hardening_logs (
    log_id TEXT PRIMARY KEY,
    initial_blueprint_id TEXT NOT NULL,
    hardened_blueprint_id TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scorecards (
    scorecard_id TEXT PRIMARY KEY,
    blueprint_id TEXT NOT NULL,
    composite_score INTEGER NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY,
    spec_id TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    data_json TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    data_json TEXT NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playbook_entries (
    entry_id TEXT PRIMARY KEY,
    attack_category TEXT NOT NULL,
    domain TEXT NOT NULL,
    data_json TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dossiers (
    dossier_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
