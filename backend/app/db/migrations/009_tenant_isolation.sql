-- Migration 009: Strict Tenant Isolation across All Stored Objects
-- Ensures all stored objects carry tenant_id for strict cross-tenant isolation and queries
ALTER TABLE hardening_logs ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE scorecards ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE policies ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE certificates ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE dossiers ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE agent_registry ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE evolve_lineage_logs ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE arena_pairings ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
ALTER TABLE seam_audit_logs ADD COLUMN tenant_id TEXT DEFAULT 'tenant-default';
