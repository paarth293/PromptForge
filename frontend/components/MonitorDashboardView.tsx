'use client';

import React, { useState, useEffect } from 'react';
import {
  Activity,
  Shield,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Clock,
  TrendingDown,
  TrendingUp,
  Cpu,
  Eye,
  Check,
  RotateCcw,
  Sliders,
  ChevronRight,
  UserCheck,
  AlertOctagon,
  FileCheck,
  ArrowUpRight
} from 'lucide-react';
import { apiFetch } from '../lib/api';

export interface MonitorScheduleData {
  schedule_id: string;
  agent_id: string;
  blueprint_id: string;
  interval_seconds: number;
  attacks_per_run: number;
  is_active: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
}

export interface MonitorRunResultData {
  run_id: string;
  agent_id: string;
  blueprint_id: string;
  baseline_survival_rate: number;
  current_survival_rate: number;
  survival_delta: number;
  baseline_goal_completion_rate?: number | null;
  current_goal_completion_rate?: number | null;
  goal_completion_delta?: number | null;
  drift_detected: boolean;
  drift_severity: 'none' | 'low' | 'medium' | 'high' | 'critical';
  drift_reasons: string[];
  formula_disclosed?: string | null;
  action_taken: 'none' | 'auto_reharden' | 'flagged_for_review';
  action_details: Record<string, any>;
  report_id?: string | null;
  executed_at: string;
}

export interface MonitorAlertData {
  alert_id: string;
  agent_id: string;
  run_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'acknowledged' | 'resolved';
  message: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface MonitorHistoryData {
  agent_id: string;
  schedules: MonitorScheduleData[];
  runs: MonitorRunResultData[];
  alerts: MonitorAlertData[];
}

interface MonitorDashboardViewProps {
  agentId: string;
  agentName?: string;
  apiBaseUrl?: string;
  tenantId?: string;
  onNavigateToAgent?: (agentId: string) => void;
}

export default function MonitorDashboardView({
  agentId,
  agentName = 'Monitored Agent',
  apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  tenantId = 'tenant-demo',
  onNavigateToAgent
}: MonitorDashboardViewProps) {
  const [history, setHistory] = useState<MonitorHistoryData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [runningAdhoc, setRunningAdhoc] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Review modal state
  const [reviewingAlert, setReviewingAlert] = useState<MonitorAlertData | null>(null);
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [reviewStatus, setReviewStatus] = useState<'acknowledged' | 'resolved'>('resolved');
  const [reviewActionApproved, setReviewActionApproved] = useState<boolean>(true);
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);

  // Tab filter
  const [alertFilter, setAlertFilter] = useState<'all' | 'open' | 'resolved'>('all');
  const [activeViewTab, setActiveViewTab] = useState<'overview' | 'runs' | 'alerts' | 'rehardening'>('overview');

  const fetchHistory = async () => {
    if (!agentId) return;
    try {
      setError(null);
      const res = await apiFetch(`${apiBaseUrl}/api/monitor/history/${agentId}`, {}, tenantId);
      if (!res.ok) {
        throw new Error(`Failed to load monitor history: HTTP ${res.status}`);
      }
      const data: MonitorHistoryData = await res.json();
      setHistory(data);
    } catch (err: any) {
      console.error('Error fetching monitor history:', err);
      setError(err.message || 'Failed to load monitor data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [agentId, apiBaseUrl, tenantId]);

  const handleManualReattack = async () => {
    setRunningAdhoc(true);
    setError(null);
    try {
      const res = await apiFetch(`${apiBaseUrl}/api/monitor/run/${agentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          attacks_per_run: 5,
          drift_threshold: 0.10,
          check_goal_completion: true
        })
      }, tenantId);

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Re-attack failed with status ${res.status}`);
      }

      // Refresh monitor history immediately
      await fetchHistory();
    } catch (err: any) {
      setError(err.message || 'Trigger re-attack run failed');
    } finally {
      setRunningAdhoc(false);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingAlert) return;

    setSubmittingReview(true);
    try {
      const res = await apiFetch(`${apiBaseUrl}/api/monitor/alerts/${reviewingAlert.alert_id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: reviewStatus,
          reviewer_notes: reviewNotes,
          action_approved: reviewActionApproved
        })
      }, tenantId);

      if (!res.ok) {
        throw new Error(`Failed to submit review: HTTP ${res.status}`);
      }

      setReviewingAlert(null);
      setReviewNotes('');
      await fetchHistory();
    } catch (err: any) {
      alert(`Error submitting review: ${err.message}`);
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400 mx-auto mb-3" />
        <p className="text-sm">Connecting to autonomous monitor service...</p>
      </div>
    );
  }

  const runs = history?.runs || [];
  const alerts = history?.alerts || [];
  const schedule = history?.schedules?.[0] || null;

  const latestRun = runs.length > 0 ? runs[0] : null;
  const openAlertsCount = alerts.filter(a => a.status === 'open').length;
  const autoRehardenEvents = runs.filter(r => r.action_taken === 'auto_reharden');

  // Filtered alerts
  const filteredAlerts = alerts.filter(a => {
    if (alertFilter === 'open') return a.status === 'open';
    if (alertFilter === 'resolved') return a.status !== 'open';
    return true;
  });

  // Render SVG Sparkline Chart of Historical Survival Scores
  const renderScoreChart = () => {
    if (runs.length === 0) {
      return (
        <div className="h-44 flex items-center justify-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
          No execution runs recorded yet. Trigger a re-attack job to initialize drift history.
        </div>
      );
    }

    // Chronological order (oldest to newest for plotting)
    const chronoRuns = [...runs].reverse();
    const width = 600;
    const height = 160;
    const padding = 30;

    const points = chronoRuns.map((r, i) => {
      const x = padding + (i / Math.max(chronoRuns.length - 1, 1)) * (width - padding * 2);
      const y = height - padding - (r.current_survival_rate * (height - padding * 2));
      return { x, y, run: r };
    });

    const pathD = points.length > 1
      ? points.reduce((acc, p, i) => i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`, '')
      : `M ${points[0]?.x || 0} ${points[0]?.y || 0}`;

    const baselineY = height - padding - ((latestRun?.baseline_survival_rate ?? 1.0) * (height - padding * 2));

    return (
      <div className="relative w-full overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-44 overflow-visible">
          {/* Baseline Reference Line */}
          <line
            x1={padding}
            y1={baselineY}
            x2={width - padding}
            y2={baselineY}
            stroke="#f59e0b"
            strokeDasharray="4 4"
            strokeWidth="1.5"
            opacity="0.8"
          />
          <text
            x={width - padding + 5}
            y={baselineY + 4}
            fill="#f59e0b"
            fontSize="10"
            fontFamily="monospace"
          >
            Baseline: {((latestRun?.baseline_survival_rate ?? 1.0) * 100).toFixed(0)}%
          </text>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((v) => {
            const y = height - padding - (v * (height - padding * 2));
            return (
              <g key={v}>
                <line
                  x1={padding}
                  y1={y}
                  x2={width - padding}
                  y2={y}
                  stroke="#334155"
                  strokeWidth="0.5"
                  opacity="0.4"
                />
                <text
                  x={padding - 24}
                  y={y + 3}
                  fill="#64748b"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {(v * 100).toFixed(0)}%
                </text>
              </g>
            );
          })}

          {/* Score Path */}
          {points.length > 1 && (
            <path
              d={pathD}
              fill="none"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Data Points */}
          {points.map((p, idx) => {
            const isDrift = p.run.drift_detected;
            const fillColor = isDrift
              ? (p.run.drift_severity === 'critical' ? '#f43f5e' : '#f97316')
              : '#10b981';

            return (
              <g key={idx} className="cursor-pointer group">
                <circle
                  cx={p.x}
                  cy={p.y}
                  r="4"
                  fill={fillColor}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                  className="transition-transform group-hover:scale-150"
                />
                <title>
                  {`Run #${idx + 1}: ${(p.run.current_survival_rate * 100).toFixed(1)}% Survival\nExecuted: ${new Date(p.run.executed_at).toLocaleString()}`}
                </title>
              </g>
            );
          })}
        </svg>

        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 px-6 font-mono">
          <span>Earliest Run: {chronoRuns[0] ? new Date(chronoRuns[0].executed_at).toLocaleDateString() : 'N/A'}</span>
          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-1 text-emerald-400">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
              <span>Observed Survival</span>
            </span>
            <span className="flex items-center space-x-1 text-amber-400">
              <span className="w-2.5 h-0.5 bg-amber-400 inline-block"></span>
              <span>Genesis Baseline</span>
            </span>
          </div>
          <span>Latest: {latestRun ? new Date(latestRun.executed_at).toLocaleTimeString() : 'N/A'}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col text-slate-100">
      {/* Top Banner & Title Bar */}
      <div className="p-6 border-b border-slate-800 bg-slate-950/70 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-white tracking-tight">Continuous Security Monitor</h2>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700 font-mono">
                STAGE 6: ACTIVE
              </span>
              {openAlertsCount > 0 && (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-700 animate-pulse font-mono">
                  {openAlertsCount} ACTION REQUIRED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Autonomous drift detection, scheduled re-attack campaigns, and human-in-the-loop escalation for <span className="text-white font-medium">{agentName}</span>.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => {
              setRefreshing(true);
              fetchHistory();
            }}
            disabled={refreshing || runningAdhoc}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleManualReattack}
            disabled={runningAdhoc || refreshing}
            className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-xs font-semibold text-white rounded-lg shadow-lg shadow-emerald-900/30 transition"
          >
            {runningAdhoc ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Executing Re-Attack...</span>
              </>
            ) : (
              <>
                <Shield className="w-3.5 h-3.5" />
                <span>Trigger Re-Attack Job</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/50 border-b border-rose-900/60 px-6 py-3 text-xs text-rose-300 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-6 bg-slate-900/50 border-b border-slate-800">
        {/* Card 1: Survival Rate */}
        <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Observed Survival</span>
            <Shield className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {latestRun ? `${(latestRun.current_survival_rate * 100).toFixed(1)}%` : '100%'}
          </div>
          <div className="mt-2 text-[11px] flex items-center space-x-1">
            {latestRun && latestRun.survival_delta > 0 ? (
              <span className="text-rose-400 flex items-center font-mono">
                <TrendingDown className="w-3 h-3 mr-0.5" />
                -{(latestRun.survival_delta * 100).toFixed(1)}% vs baseline
              </span>
            ) : (
              <span className="text-emerald-400 flex items-center font-mono">
                <CheckCircle2 className="w-3 h-3 mr-0.5" />
                Within baseline bounds
              </span>
            )}
          </div>
        </div>

        {/* Card 2: Goal Completion Rate */}
        <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Goal Journey Success</span>
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {latestRun?.current_goal_completion_rate !== null && latestRun?.current_goal_completion_rate !== undefined
              ? `${(latestRun.current_goal_completion_rate * 100).toFixed(1)}%`
              : '100.0%'}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 font-mono">
            {latestRun?.goal_completion_delta !== null && latestRun?.goal_completion_delta !== undefined
              ? `Δ: ${(latestRun.goal_completion_delta * 100).toFixed(1)}%`
              : 'Baseline intact'}
          </div>
        </div>

        {/* Card 3: Drift & Alert Status */}
        <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Drift Health</span>
            <AlertOctagon className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-lg font-bold tracking-tight mt-1 flex items-center space-x-2">
            {latestRun?.drift_detected ? (
              <span className="text-rose-400 uppercase font-mono text-base flex items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-2 animate-ping"></span>
                {latestRun.drift_severity} Drift
              </span>
            ) : (
              <span className="text-emerald-400 uppercase font-mono text-base flex items-center">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-2"></span>
                STABLE
              </span>
            )}
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            {openAlertsCount} open alert(s) in review queue
          </div>
        </div>

        {/* Card 4: Schedule Cadence */}
        <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Re-Attack Cadence</span>
            <Clock className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-white tracking-tight mt-1">
            {schedule ? `Every ${Math.round(schedule.interval_seconds / 60)}m` : 'Hourly'}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 font-mono">
            {schedule ? `${schedule.attacks_per_run} attacks / campaign` : 'Autonomous re-attack'}
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="border-b border-slate-800 px-6 flex space-x-6 text-sm">
        <button
          onClick={() => setActiveViewTab('overview')}
          className={`py-3.5 border-b-2 font-medium flex items-center space-x-2 transition ${
            activeViewTab === 'overview'
              ? 'border-emerald-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          <span>Score History & Trends</span>
        </button>

        <button
          onClick={() => setActiveViewTab('alerts')}
          className={`py-3.5 border-b-2 font-medium flex items-center space-x-2 transition ${
            activeViewTab === 'alerts'
              ? 'border-emerald-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Drift Alerts ({alerts.length})</span>
          {openAlertsCount > 0 && (
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
          )}
        </button>

        <button
          onClick={() => setActiveViewTab('rehardening')}
          className={`py-3.5 border-b-2 font-medium flex items-center space-x-2 transition ${
            activeViewTab === 'rehardening'
              ? 'border-emerald-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <RotateCcw className="w-4 h-4" />
          <span>Auto-Rehardened Events ({autoRehardenEvents.length})</span>
        </button>

        <button
          onClick={() => setActiveViewTab('runs')}
          className={`py-3.5 border-b-2 font-medium flex items-center space-x-2 transition ${
            activeViewTab === 'runs'
              ? 'border-emerald-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Execution Run Transcripts ({runs.length})</span>
        </button>
      </div>

      {/* Tab 1: Overview & Trend Chart */}
      {activeViewTab === 'overview' && (
        <div className="p-6 space-y-6">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-white">Historical Adversarial Survival Over Time</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Tracks agent defense score against Genesis baseline. Drop beyond threshold triggers auto-reharden or human escalation.
                </p>
              </div>
              {latestRun?.formula_disclosed && (
                <div className="text-[11px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1 rounded-md">
                  {latestRun.formula_disclosed}
                </div>
              )}
            </div>
            {renderScoreChart()}
          </div>

          {/* Quick Drift Summary & Latest Action */}
          {latestRun && (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                Latest Re-Attack Run Assessment (#{latestRun.run_id.slice(0, 8)})
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg">
                  <span className="text-slate-400 block mb-1">Action Dispatched:</span>
                  <span className="font-mono font-semibold text-white uppercase">{latestRun.action_taken}</span>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg">
                  <span className="text-slate-400 block mb-1">Drift Delta:</span>
                  <span className="font-mono font-semibold text-white">
                    {(latestRun.survival_delta * 100).toFixed(1)}% (Threshold: 10.0%)
                  </span>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg">
                  <span className="text-slate-400 block mb-1">Executed At:</span>
                  <span className="font-mono text-slate-300">
                    {new Date(latestRun.executed_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {latestRun.drift_reasons.length > 0 && (
                <div className="mt-4 bg-rose-950/20 border border-rose-900/40 p-3.5 rounded-lg text-xs">
                  <span className="font-semibold text-rose-300 block mb-1">Observed Degradation Reasons:</span>
                  <ul className="list-disc list-inside space-y-1 text-rose-200">
                    {latestRun.drift_reasons.map((r, idx) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Drift Alerts List */}
      {activeViewTab === 'alerts' && (
        <div className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400">Filter Alerts:</span>
              {(['all', 'open', 'resolved'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setAlertFilter(f)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium uppercase transition ${
                    alertFilter === f
                      ? 'bg-slate-800 text-white border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <span className="text-xs text-slate-500 font-mono">
              Showing {filteredAlerts.length} of {alerts.length} alerts
            </span>
          </div>

          {filteredAlerts.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              No drift alerts matching filter.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAlerts.map(alert => {
                const isOpen = alert.status === 'open';
                const severityColors = {
                  critical: 'bg-rose-950/60 border-rose-800/80 text-rose-200',
                  high: 'bg-orange-950/60 border-orange-800/80 text-orange-200',
                  medium: 'bg-amber-950/60 border-amber-800/80 text-amber-200',
                  low: 'bg-sky-950/60 border-sky-800/80 text-sky-200'
                }[alert.severity];

                return (
                  <div
                    key={alert.alert_id}
                    className={`p-4 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                      isOpen ? 'bg-slate-950 border-rose-900/60 shadow-lg shadow-rose-950/10' : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center space-x-2.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-mono font-bold border ${severityColors}`}>
                          {alert.severity}
                        </span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-mono font-semibold ${
                            isOpen ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          }`}
                        >
                          {alert.status}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          {new Date(alert.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-slate-200">{alert.message}</p>
                      {alert.metadata?.reviewer_notes && (
                        <p className="text-xs text-slate-400 bg-slate-900 border border-slate-800 p-2 rounded">
                          <span className="text-emerald-400 font-semibold">Operator Note:</span> {alert.metadata.reviewer_notes}
                        </p>
                      )}
                    </div>

                    {isOpen ? (
                      <button
                        onClick={() => {
                          setReviewingAlert(alert);
                          setReviewNotes('');
                        }}
                        className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white rounded-lg shadow transition flex items-center space-x-1.5"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        <span>Review & Resolve</span>
                      </button>
                    ) : (
                      <div className="text-right text-[11px] text-slate-500 font-mono">
                        <div>ID: {alert.alert_id}</div>
                        {alert.metadata?.reviewed_by && <div>By: {alert.metadata.reviewed_by}</div>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Auto-Rehardening Action Log */}
      {activeViewTab === 'rehardening' && (
        <div className="p-6 space-y-4">
          <div className="text-xs text-slate-400">
            Autonomous targeted hardening passes triggered when moderate drift is detected. Repoints deployments without downtime.
          </div>

          {autoRehardenEvents.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              No automated re-harden events on record. Agent defense has remained within baseline thresholds.
            </div>
          ) : (
            <div className="space-y-4">
              {autoRehardenEvents.map(run => (
                <div key={run.run_id} className="bg-slate-950 border border-emerald-900/40 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                      <h4 className="text-sm font-semibold text-white">Targeted Hardening Loop Dispatched</h4>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">
                      {new Date(run.executed_at).toLocaleString()}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs mb-3">
                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block mb-1">Pre-Harden Survival:</span>
                      <span className="font-mono text-rose-400 font-semibold">
                        {(run.action_details?.pre_harden_survival_rate * 100 || 0).toFixed(1)}%
                      </span>
                    </div>
                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block mb-1">Post-Harden Survival:</span>
                      <span className="font-mono text-emerald-400 font-semibold">
                        {(run.action_details?.post_harden_survival_rate * 100 || 0).toFixed(1)}%
                      </span>
                    </div>
                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block mb-1">Patches Applied:</span>
                      <span className="font-mono text-white font-semibold">
                        {run.action_details?.patches_applied ?? 1} Surgical Patch(es)
                      </span>
                    </div>
                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                      <span className="text-slate-400 block mb-1">Hardened Revision:</span>
                      <span className="font-mono text-indigo-300">
                        {run.action_details?.hardened_blueprint_id?.slice(0, 16) || 'active'}...
                      </span>
                    </div>
                  </div>

                  {run.action_details?.hardened_blueprint_id && onNavigateToAgent && (
                    <button
                      onClick={() => onNavigateToAgent(agentId)}
                      className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center space-x-1 mt-2 font-medium"
                    >
                      <span>View updated deployment package</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Execution Run Transcripts */}
      {activeViewTab === 'runs' && (
        <div className="p-6 space-y-3">
          {runs.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              No historical monitor runs recorded.
            </div>
          ) : (
            <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-xl overflow-hidden bg-slate-950">
              {runs.map((r, idx) => (
                <div key={r.run_id} className="p-4 flex flex-wrap items-center justify-between gap-4 text-xs">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-semibold text-white">Run #{runs.length - idx}</span>
                      <span className="text-slate-500 font-mono">({r.run_id.slice(0, 8)})</span>
                      <span
                        className={`px-2 py-0.5 rounded-full font-mono text-[10px] uppercase ${
                          r.drift_detected
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        }`}
                      >
                        {r.drift_detected ? `Drift (${r.drift_severity})` : 'Stable'}
                      </span>
                    </div>
                    <p className="text-slate-400 mt-1 font-mono">
                      Survival: {(r.current_survival_rate * 100).toFixed(1)}% | Baseline: {(r.baseline_survival_rate * 100).toFixed(1)}% | Delta: {(r.survival_delta * 100).toFixed(1)}%
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="font-mono text-slate-400 block">
                      Action: <strong className="text-white uppercase">{r.action_taken}</strong>
                    </span>
                    <span className="text-slate-500 text-[11px] font-mono">
                      {new Date(r.executed_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Review Modal Dialog */}
      {reviewingAlert && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <UserCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Operator Alert Escalation Review</h3>
              </div>
              <button
                onClick={() => setReviewingAlert(null)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg text-xs space-y-1">
              <span className="text-slate-400 block font-mono">Alert: {reviewingAlert.alert_id}</span>
              <p className="text-rose-300 font-medium">{reviewingAlert.message}</p>
            </div>

            <form onSubmit={handleReviewSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-slate-300 block mb-1">Resolution Status</label>
                <select
                  value={reviewStatus}
                  onChange={(e) => setReviewStatus(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="resolved">Resolved (Close Alert)</option>
                  <option value="acknowledged">Acknowledged (Keep in Queue)</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-300 block mb-1">Operator Notes / Rationale</label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Explain compensating controls, policy updates, or verified false positive..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-white focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>

              <div className="flex items-center space-x-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  id="approveAction"
                  checked={reviewActionApproved}
                  onChange={(e) => setReviewActionApproved(e.target.checked)}
                  className="rounded border-slate-800 text-emerald-600 focus:ring-0"
                />
                <label htmlFor="approveAction">Sign off and approve action taken in audit trail</label>
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setReviewingAlert(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReview}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white rounded-lg transition shadow"
                >
                  {submittingReview ? 'Submitting...' : 'Submit Resolution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
