-- Migration 010: Composite Indexes for Scaled Query Performance
-- Eliminates full table scans on tenant-, blueprint-, and agent-scoped queries.

CREATE INDEX IF NOT EXISTS idx_specs_tenant_created ON specs (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_blueprints_tenant_created ON blueprints (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_blueprints_spec_id ON blueprints (spec_id);
CREATE INDEX IF NOT EXISTS idx_deployments_tenant_deployed ON deployments (tenant_id, deployed_at DESC);
CREATE INDEX IF NOT EXISTS idx_deployments_agent_id ON deployments (agent_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_tenant_created ON dossiers (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dossiers_agent_id ON dossiers (agent_id);

CREATE INDEX IF NOT EXISTS idx_redteam_blueprint_created ON redteam_reports (blueprint_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_redteam_tenant_created ON redteam_reports (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scorecards_blueprint_created ON scorecards (blueprint_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scorecards_tenant_created ON scorecards (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_hardening_logs_initial_bp ON hardening_logs (initial_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_hardening_logs_hardened_bp ON hardening_logs (hardened_blueprint_id);
CREATE INDEX IF NOT EXISTS idx_hardening_logs_tenant ON hardening_logs (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_policies_spec_created ON policies (spec_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_policies_tenant ON policies (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_agent_timestamp ON audit_events (agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_timestamp ON audit_events (tenant_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_monitor_runs_agent_created ON monitor_runs (agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_runs_tenant ON monitor_runs (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_monitor_alerts_agent_created ON monitor_alerts (agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_alerts_tenant ON monitor_alerts (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_alerts_run_id ON monitor_alerts (run_id);
