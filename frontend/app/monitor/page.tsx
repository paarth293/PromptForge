'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Activity,
  Shield,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Search,
  ArrowRight,
  UserCheck,
  Zap,
  Server,
  ChevronRight,
  Cpu
} from 'lucide-react';
import MonitorDashboardView, { MonitorAlertData } from '../../components/MonitorDashboardView';
import { apiFetch } from '../../lib/api';

interface DeploymentSummary {
  deployment_id: string;
  agent_id: string;
  blueprint_id: string;
  agent_name: string;
  version: number;
  status: string;
  deployed_at: string;
}

export default function MonitorPage() {
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [deployments, setDeployments] = useState<DeploymentSummary[]>([]);
  const [reviewQueue, setReviewQueue] = useState<MonitorAlertData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningPending, setRunningPending] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const loadData = async () => {
    try {
      setLoading(true);
      // 1. Fetch deployments
      const depRes = await apiFetch(`${apiBaseUrl}/api/deploy/agents`, {}, 'tenant-demo').catch(() => null);

      let loadedDeps: DeploymentSummary[] = [];
      if (depRes && depRes.ok) {
        loadedDeps = await depRes.json();
        setDeployments(loadedDeps);
      }

      // 2. Fetch Review Queue
      const queueRes = await apiFetch(`${apiBaseUrl}/api/monitor/review-queue`, {}, 'tenant-demo').catch(() => null);

      if (queueRes && queueRes.ok) {
        const queueData: MonitorAlertData[] = await queueRes.json();
        setReviewQueue(queueData);
      }

      // Default select the first agent if available and none selected yet
      if (!selectedAgentId && loadedDeps.length > 0) {
        setSelectedAgentId(loadedDeps[0].agent_id);
      }
    } catch (e) {
      console.error('Failed to load monitor index', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [apiBaseUrl]);

  const handleRunPendingSchedules = async () => {
    setRunningPending(true);
    try {
      const res = await apiFetch(`${apiBaseUrl}/api/monitor/schedules/run-pending`, {
        method: 'POST'
      }, 'tenant-demo');
      if (res.ok) {
        await loadData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRunningPending(false);
    }
  };

  const filteredDeployments = deployments.filter(d =>
    d.agent_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.agent_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-forge-dark text-slate-100 flex flex-col">
      {/* Shared-theme header — matches UnifiedNavigationShell style */}
      <header className="w-full border-b border-forge-border bg-forge-dark/90 backdrop-blur-md sticky top-0 z-50 px-4 md:px-8 py-3 flex flex-wrap items-center gap-3">
        <Link href="/" className="flex items-center gap-2 group shrink-0">
          <div className="w-7 h-7 flex items-center justify-center rounded-lg bg-blue-600/15 text-blue-400 border border-blue-500/25 group-hover:border-blue-400/60 transition-colors">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <span className="text-sm font-bold tracking-tight text-white group-hover:text-blue-200 transition-colors">
            PromptForge
          </span>
        </Link>
        <span className="text-forge-border">/</span>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-teal-500/10 border border-teal-500/25 text-teal-300 text-xs font-medium">
          <Activity className="w-3.5 h-3.5 text-teal-400" />
          MONITOR — Drift Control Center
        </div>
        <div className="flex-1" />
        <button
          onClick={handleRunPendingSchedules}
          disabled={runningPending}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-forge-surface hover:bg-forge-surface2 disabled:opacity-50 text-xs font-medium text-slate-200 rounded-lg border border-forge-border transition"
        >
          <Zap className={`w-3.5 h-3.5 ${runningPending ? 'animate-spin text-amber-400' : 'text-amber-400'}`} />
          <span>{runningPending ? 'Executing Schedules...' : 'Run Pending Schedules'}</span>
        </button>
        <Link
          href="/"
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white rounded-lg transition"
        >
          Open Forge
        </Link>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Agent Selector & Review Queue summary (4 cols) */}
        <aside className="lg:col-span-4 space-y-6">
          {/* Review Queue Card */}
          <div className="bg-forge-surface border border-forge-border rounded-xl p-4 shadow-panel">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <h3 className="text-sm font-bold text-white">Escalation Review Queue</h3>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-bold ${
                reviewQueue.length > 0 ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
              }`}>
                {reviewQueue.length} Pending
              </span>
            </div>

            {reviewQueue.length === 0 ? (
              <p className="text-xs text-slate-400 flex items-center space-x-1.5 py-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span>All drift alerts have been acknowledged or resolved.</span>
              </p>
            ) : (
              <div className="space-y-2">
                {reviewQueue.slice(0, 3).map(alert => (
                  <div
                    key={alert.alert_id}
                    onClick={() => setSelectedAgentId(alert.agent_id)}
                    className="p-2.5 bg-forge-dark border border-rose-900/50 hover:border-rose-500 rounded-lg cursor-pointer transition text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-rose-300 uppercase font-bold">{alert.severity}</span>
                      <span className="font-mono text-[10px] text-slate-500">{alert.agent_id.slice(0, 12)}</span>
                    </div>
                    <p className="text-slate-300 line-clamp-1">{alert.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Deployed Agents List Card */}
          <div className="bg-forge-surface border border-forge-border rounded-xl p-4 shadow-panel space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Server className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Monitored Fleet</h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">{deployments.length} Deployed</span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search agent by name or ID..."
                className="w-full bg-forge-dark border border-forge-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Agent List */}
            {filteredDeployments.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-forge-border rounded-lg">
                No agents match search.
              </div>
            ) : (
              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {filteredDeployments.map(dep => {
                  const isSelected = selectedAgentId === dep.agent_id;
                  return (
                    <div
                      key={dep.agent_id}
                      onClick={() => setSelectedAgentId(dep.agent_id)}
                      className={`p-3 rounded-lg border cursor-pointer transition text-xs flex items-center justify-between ${
                        isSelected
                          ? 'bg-forge-dark border-emerald-500/80 shadow-md shadow-emerald-950/20'
                          : 'bg-forge-dark/60 border-forge-border hover:border-slate-600'
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-white">{dep.agent_name}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-forge-surface text-slate-300 font-mono">
                            v{dep.version}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono truncate max-w-[200px]">
                          {dep.agent_id}
                        </div>
                      </div>
                      <ChevronRight className={`w-4 h-4 ${isSelected ? 'text-emerald-400' : 'text-slate-600'}`} />
                    </div>
                  );
                })}
              </div>
            )}

            {/* Quick manual agent ID input fallback */}
            <div className="pt-2 border-t border-forge-border flex space-x-2">
              <input
                type="text"
                placeholder="Or enter any agent ID..."
                value={selectedAgentId}
                onChange={(e) => setSelectedAgentId(e.target.value)}
                className="flex-1 bg-forge-dark border border-forge-border rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
              />
            </div>
          </div>
        </aside>

        {/* Right Column: Selected Agent Monitor Dashboard (8 cols) */}
        <main className="lg:col-span-8">
          {selectedAgentId ? (
            <MonitorDashboardView
              agentId={selectedAgentId}
              agentName={deployments.find(d => d.agent_id === selectedAgentId)?.agent_name || selectedAgentId}
              apiBaseUrl={apiBaseUrl}
              tenantId="tenant-demo"
              onNavigateToAgent={(aid) => {
                window.location.href = `/agents/${aid}`;
              }}
            />
          ) : (
            <div className="bg-forge-surface border border-forge-border rounded-2xl p-16 text-center text-slate-400">
              <Activity className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-bold text-white mb-1">Select an Agent to Monitor</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Choose an agent from the fleet on the left to inspect its historical survival scores, active drift alerts, and re-hardening event log.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
