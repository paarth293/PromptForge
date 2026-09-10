'use client';

import React, { useEffect, useState, useRef } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Cpu,
  RefreshCw,
  Scale,
  Hash,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Zap,
  Terminal
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AttackVerdictData {
  id: string;
  attack_id?: string;
  session_id?: string;
  category: string;
  attacker_persona: string;
  attacker_model: string;
  prompt: string;
  response: string;
  verdict: 'BLOCKED' | 'DEGRADED' | 'COMPROMISED';
  verdict_rationale?: string;
  cited_evidence: string;
  violation_detected: boolean;
  violated_boundary_or_policy?: string | null;
  severity_score: number;
  judge_model: string;
  cross_check_model?: string | null;
  cross_check_verdict?: string | null;
  cross_check_agrees?: boolean | null;
  created_at: string;
}

export interface RedTeamReportData {
  report_id: string;
  blueprint_id: string;
  tenant_id: string;
  total_attacks: number;
  blocked_count: number;
  degraded_count: number;
  compromised_count: number;
  survival_rate: number;
  category_breakdown: Record<string, { BLOCKED: number; DEGRADED: number; COMPROMISED: number; total: number }>;
  difficulty_mix: Record<string, number>;
  attack_verdicts: AttackVerdictData[];
  cross_check_agreement_rate?: number | null;
  report_hash?: string | null;
  created_at: string;
}

interface RedTeamFeedProps {
  blueprintId: string;
  agentName: string;
  tenantId?: string;
  onBackToChat?: () => void;
  onProceedToHardening?: (report: RedTeamReportData) => void;
}

export default function RedTeamFeed({
  blueprintId,
  agentName,
  tenantId = 'tenant-demo',
  onBackToChat,
  onProceedToHardening
}: RedTeamFeedProps) {
  const [running, setRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Ready to launch Red Team attack campaign.');
  const [currentStage, setCurrentStage] = useState<string>('idle');
  const [totalExpected, setTotalExpected] = useState<number>(0);
  const [completedCount, setCompletedCount] = useState<number>(0);
  const [verdicts, setVerdicts] = useState<AttackVerdictData[]>([]);
  const [report, setReport] = useState<RedTeamReportData | null>(null);
  const [agreementRate, setAgreementRate] = useState<number | null>(null);
  const [expandedVerdictId, setExpandedVerdictId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-start campaign on mount
  useEffect(() => {
    startRedTeamStream();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [blueprintId]);

  const startRedTeamStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setRunning(true);
    setError(null);
    setVerdicts([]);
    setReport(null);
    setCompletedCount(0);
    setStatusMessage('Initializing 3-axis diverse attacker campaign...');
    setCurrentStage('generating');

    try {
      const sseUrl = `${API_BASE_URL}/api/redteam/stream/${blueprintId}?attacks_per_persona=3&concurrency=8&tenant_id=${encodeURIComponent(tenantId)}`;
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'status') {
            setStatusMessage(data.message);
            setCurrentStage(data.stage);
          } else if (data.type === 'campaign_init') {
            setTotalExpected(data.total_attacks);
            setStatusMessage(`Gated Campaign Ready: ${data.total_attacks} attacks queued.`);
          } else if (data.type === 'verdict') {
            setCompletedCount(data.completed);
            setTotalExpected(data.total);
            setVerdicts((prev) => [data.verdict, ...prev]);
            setStatusMessage(`Evaluated attack ${data.completed}/${data.total} — Verdict: ${data.verdict.verdict}`);
          } else if (data.type === 'cross_check_complete') {
            setAgreementRate(data.agreement_rate);
            setStatusMessage(`Cross-check complete (${(data.agreement_rate * 100).toFixed(1)}% agreement rate).`);
          } else if (data.type === 'report_ready') {
            setReport(data.report);
            setRunning(false);
            setStatusMessage('Red Team pass complete. Final report generated and hashed.');
            es.close();
          }
        } catch (err: any) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      es.onerror = (err) => {
        console.warn('SSE stream error or closed, falling back to REST endpoint:', err);
        es.close();
        // Fallback to direct POST execution if SSE disconnects
        fetchFallbackReport();
      };
    } catch (err: any) {
      setError(err.message || 'Failed to initialize Red Team stream');
      setRunning(false);
    }
  };

  const fetchFallbackReport = async () => {
    try {
      setStatusMessage('Querying latest Red Team report from repository...');
      const res = await fetch(`${API_BASE_URL}/api/redteam/run/${blueprintId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': tenantId
        },
        body: JSON.stringify({ attacks_per_persona: 3, concurrency: 8 })
      });

      if (res.ok) {
        const rep: RedTeamReportData = await res.json();
        setReport(rep);
        setVerdicts(rep.attack_verdicts || []);
        setAgreementRate(rep.cross_check_agreement_rate ?? null);
        setTotalExpected(rep.total_attacks);
        setCompletedCount(rep.total_attacks);
        setStatusMessage('Red Team report loaded successfully.');
      } else {
        throw new Error(`Report endpoint returned status ${res.status}`);
      }
    } catch (err: any) {
      setError('Could not retrieve Red Team results.');
    } finally {
      setRunning(false);
    }
  };

  // Compute live counts
  const blockedCount = verdicts.filter((v) => v.verdict.toUpperCase() === 'BLOCKED').length;
  const degradedCount = verdicts.filter((v) => v.verdict.toUpperCase() === 'DEGRADED').length;
  const compromisedCount = verdicts.filter((v) => v.verdict.toUpperCase() === 'COMPROMISED').length;
  const totalCount = verdicts.length;
  const survivalRate = totalCount > 0 ? (blockedCount / totalCount) * 100 : 100;

  const toggleExpand = (id: string) => {
    setExpandedVerdictId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="w-full max-w-5xl flex flex-col gap-6">
      {/* Header / Nav */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#151C2C] border border-[#232D42] rounded-2xl p-5 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-red-500/20 text-red-400 rounded-xl border border-red-500/30">
            <Flame className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                Stage 2: Red Team Evaluation
              </h2>
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/30">
                {agentName}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              3-Axis Diversity • 5+ Personas • Open-Weight Ollama • Non-Circular Judging
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {onBackToChat && (
            <button
              onClick={onBackToChat}
              className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              ← Back to Chat
            </button>
          )}
          <button
            onClick={startRedTeamStream}
            disabled={running}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white shadow-lg shadow-red-600/20 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Attacking...' : 'Re-Run Red Team'}
          </button>
          {onProceedToHardening && report && (
            <button
              onClick={() => onProceedToHardening(report)}
              disabled={running}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white shadow-lg shadow-emerald-600/20 transition"
            >
              <span>Hardening Loop (Stage 2.5)</span>
              <span>→</span>
            </button>
          )}
        </div>
      </div>

      {/* Live Status Banner */}
      <div className="flex items-center justify-between bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-3 text-xs">
        <div className="flex items-center gap-2 text-slate-300">
          <span className={`w-2.5 h-2.5 rounded-full ${running ? 'bg-amber-400 animate-ping' : 'bg-emerald-400'}`} />
          <span className="font-medium text-slate-200">{statusMessage}</span>
        </div>
        <div className="text-slate-400 font-mono text-[11px]">
          {totalExpected > 0 ? `${completedCount} / ${totalExpected} evaluated` : `${completedCount} verdicts`}
        </div>
      </div>

      {/* Live Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {/* Survival Rate Card */}
        <div className="p-4 bg-[#151C2C] border border-[#232D42] rounded-xl flex flex-col justify-between">
          <div className="text-slate-400 text-xs font-medium">Survival Rate</div>
          <div
            className={`text-2xl font-bold tracking-tight mt-1 ${
              survivalRate >= 90 ? 'text-emerald-400' : survivalRate >= 70 ? 'text-amber-400' : 'text-red-400'
            }`}
          >
            {survivalRate.toFixed(1)}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Clean BLOCKED ratio</div>
        </div>

        {/* Blocked Card */}
        <div className="p-4 bg-[#151C2C] border border-[#232D42] rounded-xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Blocked</span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 tracking-tight mt-1">{blockedCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Guarded securely</div>
        </div>

        {/* Degraded Card */}
        <div className="p-4 bg-[#151C2C] border border-[#232D42] rounded-xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Degraded</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 tracking-tight mt-1">{degradedCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Role/tone slip</div>
        </div>

        {/* Compromised Card */}
        <div className="p-4 bg-[#151C2C] border border-[#232D42] rounded-xl flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Compromised</span>
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400 tracking-tight mt-1">{compromisedCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Policy breach</div>
        </div>

        {/* Cross Check Agreement Card */}
        <div className="p-4 bg-[#151C2C] border border-[#232D42] rounded-xl flex flex-col justify-between col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Judge Consensus</span>
            <Scale className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 tracking-tight mt-1">
            {agreementRate !== null ? `${(agreementRate * 100).toFixed(0)}%` : '—'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">20% cross-checked</div>
        </div>
      </div>

      {/* Cryptographic Report Hash (When Ready) */}
      {report && report.report_hash && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-blue-950/20 border border-blue-500/30 rounded-xl px-4 py-3 text-xs text-blue-300 gap-2">
          <div className="flex items-center gap-2">
            <Hash className="w-4 h-4 text-blue-400" />
            <span className="font-semibold">Cryptographic Audit Fingerprint:</span>
            <span className="font-mono text-[11px] text-blue-200">{report.report_hash}</span>
          </div>
          <span className="text-[10px] text-blue-400 uppercase font-bold tracking-wider">
            Tamper-Evident SHA-256
          </span>
        </div>
      )}

      {/* Live Streaming Verdict Feed */}
      <div className="bg-[#151C2C] border border-[#232D42] rounded-2xl p-5 shadow-xl flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-white tracking-tight">Live Adversarial Verdict Feed</h3>
            {running && (
              <span className="flex items-center gap-1 text-[10px] uppercase font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                Live
              </span>
            )}
          </div>
          <span className="text-xs text-slate-400">{verdicts.length} attack outcomes recorded</span>
        </div>

        {verdicts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500 text-xs">
            <Cpu className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
            <span>Streaming verdicts as attacks land...</span>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {verdicts.map((v, i) => {
              const isExpanded = expandedVerdictId === v.id;
              const verdictStyle =
                v.verdict === 'BLOCKED'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : v.verdict === 'DEGRADED'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  : 'bg-red-500/10 text-red-400 border-red-500/30';

              return (
                <div
                  key={v.id || i}
                  className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition flex flex-col gap-3"
                >
                  {/* Top line: Badges & Models */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${verdictStyle}`}>
                        {v.verdict}
                      </span>
                      <span className="text-xs font-semibold text-slate-200">
                        {v.attacker_persona}
                      </span>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                        {v.category}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700 text-slate-300">
                        Judge: <strong className="text-white">{v.judge_model}</strong>
                      </span>
                      {v.cross_check_model && (
                        <span className="px-2 py-0.5 rounded bg-blue-900/30 border border-blue-500/30 text-blue-300">
                          Cross-Check: {v.cross_check_model} ({v.cross_check_agrees ? '✓' : '≠'})
                        </span>
                      )}
                      <button
                        onClick={() => toggleExpand(v.id)}
                        className="text-slate-400 hover:text-white p-1"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Prompt & Cited Evidence Preview */}
                  <div className="text-xs text-slate-300 font-sans">
                    <span className="text-slate-500 font-semibold mr-1.5">Prompt:</span>
                    <span className="italic">{v.prompt}</span>
                  </div>

                  {v.cited_evidence && (
                    <div className="bg-slate-950/80 border-l-2 border-amber-500/80 px-3 py-2 rounded-r-lg text-xs font-mono text-amber-200/90">
                      <span className="text-amber-400/70 font-sans font-semibold mr-2">Evidence:</span>
                      &ldquo;{v.cited_evidence}&rdquo;
                    </div>
                  )}

                  {/* Expanded Transcript & Details */}
                  {isExpanded && (
                    <div className="mt-2 pt-3 border-t border-slate-800 flex flex-col gap-2 text-xs">
                      {v.verdict_rationale && (
                        <div>
                          <span className="text-slate-400 font-semibold">Judge Rationale: </span>
                          <span className="text-slate-300">{v.verdict_rationale}</span>
                        </div>
                      )}
                      {v.response && (
                        <div>
                          <span className="text-slate-400 font-semibold">Agent Full Response: </span>
                          <div className="p-2.5 bg-slate-950 rounded-lg text-slate-300 font-mono text-[11px] mt-1 whitespace-pre-wrap">
                            {v.response}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
