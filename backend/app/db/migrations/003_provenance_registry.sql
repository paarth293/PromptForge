-- Migration 003: Provenance Registry Storage
CREATE TABLE IF NOT EXISTS agent_registry (
    registry_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    blueprint_id TEXT NOT NULL,
    forger_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    watermark TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(blueprint_id) REFERENCES blueprints(blueprint_id)
);
