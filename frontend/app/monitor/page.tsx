'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Search,
  Zap,
  Server,
  ChevronRight,
  Shield
} from 'lucide-react';
import MainNav from '../../components/MainNav';
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
    <div className="min-h-screen bg-[#F9F5F0] text-[#3D3229] flex flex-col font-sans selection:bg-[#C75A3B] selection:text-white">
      {/* Global Unified Navigation Bar (Action 1 & 4) */}
      <MainNav activeStage="monitor" />

      {/* Action Strip: Schedule Controls & Overview */}
      <div className="w-full bg-[#FBF8F4] border-b border-[#E8DDD2] px-4 md:px-8 py-2.5 flex items-center justify-between gap-4 shadow-2xs">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#C75A3B]" />
          <span className="text-xs font-bold text-[#3D3229]">SOC Monitor: Fleet Telemetry &amp; Drift Detection</span>
        </div>

        <button
          onClick={handleRunPendingSchedules}
          disabled={runningPending}
          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#C75A3B] hover:bg-[#B84A2F] disabled:opacity-50 text-xs font-bold text-white rounded-lg transition shadow-xs"
        >
          <Zap className={`w-3.5 h-3.5 ${runningPending ? 'animate-spin' : ''}`} />
          <span>{runningPending ? 'Executing Schedules...' : 'Run Scheduled Probes'}</span>
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Agent Selector & Review Queue summary (4 cols) */}
        <aside className="lg:col-span-4 space-y-6">
          {/* Review Queue Card */}
          <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-4 shadow-card">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-[#E74C3C]" />
                <h3 className="text-sm font-bold text-[#3D3229]">Human Escalation Queue</h3>
              </div>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold ${
                reviewQueue.length > 0 ? 'bg-[#E74C3C]/10 text-[#E74C3C] border border-[#E74C3C]/30' : 'bg-[#2ECC71]/10 text-[#2ECC71] border border-[#2ECC71]/30'
              }`}>
                {reviewQueue.length} Pending
              </span>
            </div>

            {reviewQueue.length === 0 ? (
              <p className="text-xs text-[#666555] flex items-center space-x-1.5 py-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#2ECC71] flex-shrink-0" />
                <span>All drift alerts resolved across deployed agents.</span>
              </p>
            ) : (
              <div className="space-y-2">
                {reviewQueue.slice(0, 3).map(alert => (
                  <div
                    key={alert.alert_id}
                    onClick={() => setSelectedAgentId(alert.agent_id)}
                    className="p-2.5 bg-[#F0E6DC]/60 border border-[#E74C3C]/40 hover:border-[#E74C3C] rounded-lg cursor-pointer transition text-xs space-y-1 shadow-2xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-[#E74C3C] uppercase font-bold">{alert.severity}</span>
                      <span className="font-mono text-[10px] text-[#666555]">{alert.agent_id.slice(0, 12)}</span>
                    </div>
                    <p className="text-[#3D3229] line-clamp-1">{alert.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Deployed Agents List Card */}
          <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-4 shadow-card space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Server className="w-4 h-4 text-[#2ECC71]" />
                <h3 className="text-sm font-bold text-[#3D3229]">Monitored Fleet</h3>
              </div>
              <span className="text-xs text-[#666555] font-mono">{deployments.length} Active</span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#666555] absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search agent by name or ID..."
                className="w-full bg-white border border-[#E8DDD2] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[#3D3229] placeholder-[#9B8B7E] focus:outline-none focus:border-[#C75A3B]"
              />
            </div>

            {/* Agent List */}
            {filteredDeployments.length === 0 ? (
              <div className="p-6 text-center text-xs text-[#666555] border border-dashed border-[#E8DDD2] rounded-lg bg-[#F0E6DC]/20">
                No deployed agents found. Launch an agent in Forge first.
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
                          ? 'bg-[#F0E6DC] border-[#C75A3B] shadow-sm'
                          : 'bg-white border-[#E8DDD2] hover:bg-[#F0E6DC]/40'
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-[#3D3229]">{dep.agent_name}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#F0E6DC] text-[#666555] font-mono border border-[#E8DDD2]">
                            v{dep.version}
                          </span>
                        </div>
                        <div className="text-[10px] text-[#666555] font-mono truncate max-w-[200px]">
                          {dep.agent_id}
                        </div>
                      </div>
                      <ChevronRight className={`w-4 h-4 ${isSelected ? 'text-[#C75A3B]' : 'text-[#9B8B7E]'}`} />
                    </div>
                  );
                })}
              </div>
            )}

            {/* Quick manual agent ID input fallback */}
            <div className="pt-2 border-t border-[#E8DDD2] flex space-x-2">
              <input
                type="text"
                placeholder="Or inspect specific agent ID..."
                value={selectedAgentId}
                onChange={(e) => setSelectedAgentId(e.target.value)}
                className="flex-1 bg-white border border-[#E8DDD2] rounded-lg px-2.5 py-1.5 text-xs text-[#3D3229] placeholder-[#9B8B7E] focus:outline-none focus:border-[#C75A3B] font-mono"
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
            <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-2xl p-16 text-center text-[#666555] shadow-card">
              <Activity className="w-12 h-12 text-[#C75A3B] mx-auto mb-3 opacity-80" />
              <h3 className="text-base font-bold text-[#3D3229] mb-1">Select an Agent to Monitor</h3>
              <p className="text-xs text-[#666555] max-w-sm mx-auto">
                Choose an active agent from the fleet on the left to inspect its historical survival rates, drift alerts, and automated re-hardening log.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
