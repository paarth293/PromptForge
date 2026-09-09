-- Migration 004: Deployed Agent Packages
CREATE TABLE IF NOT EXISTS deployments (
    deployment_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    blueprint_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    shareable_url TEXT NOT NULL,
    chat_api_url TEXT NOT NULL,
    certificate_id TEXT,
    data_json TEXT NOT NULL,
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
