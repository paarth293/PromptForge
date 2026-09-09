-- Migration 005: MONITOR Stage (Schedules, Periodic Runs, Drift Alerts)
CREATE TABLE IF NOT EXISTS monitor_schedules (
    schedule_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    blueprint_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    interval_seconds INTEGER DEFAULT 3600,
    is_active INTEGER DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    attacks_per_run INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitor_runs (
    run_id TEXT PRIMARY KEY,
    schedule_id TEXT,
    agent_id TEXT NOT NULL,
    blueprint_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    baseline_survival_rate REAL NOT NULL,
    current_survival_rate REAL NOT NULL,
    survival_delta REAL NOT NULL,
    drift_detected INTEGER NOT NULL DEFAULT 0,
    drift_severity TEXT NOT NULL DEFAULT 'none',
    action_taken TEXT NOT NULL DEFAULT 'none',
    action_details TEXT,
    report_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitor_alerts (
    alert_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    message TEXT NOT NULL,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
