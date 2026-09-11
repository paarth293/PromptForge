-- Migration 011: API Keys Authentication and Deployment Share Tokens
-- Enforces cryptographic API key validation and secure deployment share links.

CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    scopes TEXT NOT NULL DEFAULT '["*"]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id);

ALTER TABLE deployments ADD COLUMN share_token TEXT;
CREATE INDEX IF NOT EXISTS idx_deployments_share_token ON deployments (share_token);
