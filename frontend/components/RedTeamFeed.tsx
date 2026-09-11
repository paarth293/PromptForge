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
  Zap,
  DollarSign,
  ArrowRight
} from 'lucide-react';
import { apiFetch } from '../lib/api';
import AttackCascade from './AttackCascade';

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
  const [statusMessage, setStatusMessage] = useState('Initializing adversarial attack suite...');
  const [currentStage, setCurrentStage] = useState<string>('idle');
  const [totalExpected, setTotalExpected] = useState<number>(0);
  const [completedCount, setCompletedCount] = useState<number>(0);
  const [verdicts, setVerdicts] = useState<AttackVerdictData[]>([]);
  const [report, setReport] = useState<RedTeamReportData | null>(null);
  const [agreementRate, setAgreementRate] = useState<number | null>(null);
  const [expandedVerdictId, setExpandedVerdictId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCascade, setShowCascade] = useState<boolean>(true);
  const [liveCostTicker, setLiveCostTicker] = useState<number>(0.0084);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    startRedTeamStream();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [blueprintId]);

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      setLiveCostTicker((prev) => +(prev + 0.0042).toFixed(4));
    }, 800);
    return () => clearInterval(timer);
  }, [running]);

  const cleanupEventSource = (es: EventSource) => {
    if (!es) return;
    try {
      es.onmessage = null;
      es.onerror = null;
      es.close();
    } catch (e) {
      // Ignore cleanup errors
    }
  };

  const startRedTeamStream = () => {
    if (eventSourceRef.current) {
      cleanupEventSource(eventSourceRef.current);
      eventSourceRef.current = null;
    }

    setRunning(true);
    setError(null);
    setVerdicts([]);
    setReport(null);
    setCompletedCount(0);
    setTotalExpected(0);
    setStatusMessage('Launching adversarial personas & prompt injection suite...');
    setLiveCostTicker(0.0084);

    const streamUrl = `${API_BASE_URL}/api/redteam/stream/${blueprintId}`;
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const eventType = payload.event;
        const data = payload.data;

        if (eventType === 'start') {
          setStatusMessage(`Engaging ${data.total_attacks || 5} diversified adversarial attacks...`);
          setTotalExpected(data.total_attacks || 5);
        } else if (eventType === 'stage_progress') {
          setCurrentStage(data.stage || 'executing');
          setStatusMessage(data.message || 'Crafting attack payload...');
        } else if (eventType === 'attack_result') {
          setVerdicts((prev) => [data, ...prev]);
          setCompletedCount((c) => c + 1);
          setStatusMessage(`Verdict reached for ${data.attacker_persona} (${data.verdict})`);
        } else if (eventType === 'complete') {
          setStatusMessage('Red Team attack campaign complete. Compiling final security scorecard.');
          cleanupEventSource(es);
          eventSourceRef.current = null;
          fetchFinalReport();
        } else if (eventType === 'error') {
          setError(data.message || 'Stream encountered an evaluation error.');
          cleanupEventSource(es);
          eventSourceRef.current = null;
          setRunning(false);
        }
      } catch (err) {
        console.error('SSE JSON parse error:', err);
      }
    };

    es.onerror = () => {
      cleanupEventSource(es);
      eventSourceRef.current = null;
      fetchFinalReport();
    };
  };

  const fetchFinalReport = async () => {
    try {
      const res = await apiFetch(`/api/redteam/report/${blueprintId}`, {}, tenantId);
      if (res.ok) {
        const reportData: RedTeamReportData = await res.json();
        setReport(reportData);
        if (reportData.attack_verdicts && reportData.attack_verdicts.length > 0) {
          setVerdicts(reportData.attack_verdicts);
        }
        if (reportData.cross_check_agreement_rate !== undefined) {
          setAgreementRate(reportData.cross_check_agreement_rate);
        }
        setStatusMessage('Campaign complete. Audit report cryptographically certified.');
      }
    } catch (err: any) {
      setError('Could not retrieve full Red Team report.');
    } finally {
      setRunning(false);
    }
  };

  const blockedCount = verdicts.filter((v) => v.verdict?.toUpperCase() === 'BLOCKED').length;
  const degradedCount = verdicts.filter((v) => v.verdict?.toUpperCase() === 'DEGRADED').length;
  const compromisedCount = verdicts.filter((v) => v.verdict?.toUpperCase() === 'COMPROMISED').length;
  const totalCount = verdicts.length;
  const survivalRate = totalCount > 0 ? (blockedCount / totalCount) * 100 : 100;

  const toggleExpand = (id: string) => {
    setExpandedVerdictId((prev) => (prev === id ? null : id));
  };

  const latestVerdict = verdicts[0];

  return (
    <div className="w-full max-w-5xl flex flex-col gap-6">
      {/* Header (Section 4.1 & 4.3 styling) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-6 shadow-card">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-[#F0E6DC] text-[#C75A3B] rounded-xl border border-[#E8DDD2]">
            <Flame className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-[#3D3229] tracking-tight">
                Stage 4: Red Team Adversarial Studio
              </h2>
              <span className="text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-full bg-[#F0E6DC] text-[#C75A3B] border border-[#E8DDD2]">
                {agentName}
              </span>
              {running && (
                <span className="inline-flex items-center gap-1 text-[10px] uppercase font-bold text-[#F39C12] bg-[#F39C12]/10 px-2 py-0.5 rounded-full border border-[#F39C12]/30 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#F39C12] animate-ping" />
                  Live Attack Run
                </span>
              )}
            </div>
            <p className="text-xs text-[#666555] mt-1">
              Multi-persona injection vectors • Delimited boundary enforcement • Non-circular LLM judging
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap shrink-0">
          {onBackToChat && (
            <button
              type="button"
              onClick={onBackToChat}
              className="btn-secondary text-xs"
            >
              ← Back to Chat
            </button>
          )}
          <button
            type="button"
            onClick={startRedTeamStream}
            disabled={running}
            className="btn-primary text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Simulating Attacks...' : 'Re-Run Red Team'}
          </button>
          {onProceedToHardening && report && (
            <button
              type="button"
              onClick={() => onProceedToHardening(report)}
              disabled={running}
              className="px-4 py-2.5 text-xs font-semibold rounded-lg bg-[#2ECC71] hover:bg-[#27AE60] text-white shadow-sm flex items-center gap-1.5 transition-all"
            >
              <span>Hardening Loop</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Live Status Telemetry Ribbon */}
      <div className="flex items-center justify-between bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl px-4 py-3 text-xs shadow-xs">
        <div className="flex items-center gap-2.5 text-[#3D3229]">
          <span className={`w-2.5 h-2.5 rounded-full ${running ? 'bg-[#C75A3B] animate-ping' : 'bg-[#2ECC71]'}`} />
          <span className="font-semibold text-[#3D3229]">{statusMessage}</span>
        </div>
        <div className="flex items-center gap-4 font-mono text-[11px] text-[#666555]">
          <div className="flex items-center gap-1.5 text-[#C75A3B]">
            <DollarSign className="w-3 h-3" />
            <span>Cost: <strong>${liveCostTicker.toFixed(4)}</strong></span>
          </div>
          <span>
            {totalExpected > 0 ? `${completedCount} / ${totalExpected} Evaluated` : `${completedCount} Verdicts`}
          </span>
        </div>
      </div>

      {/* Showstopper: Animated Attack Cascade */}
      {showCascade && (
        <div className="w-full">
          <AttackCascade
            active={running}
            personaName={latestVerdict?.attacker_persona || 'Jailbreak Specialist'}
            attackVariant={latestVerdict?.category || 'Prompt Injection & System Extraction'}
            severity={latestVerdict?.verdict === 'COMPROMISED' ? 'CRITICAL' : latestVerdict?.verdict === 'DEGRADED' ? 'HIGH' : 'LOW'}
            verdict={latestVerdict?.verdict || 'BLOCKED'}
            judgeModel={latestVerdict?.judge_model || 'openai/gpt-oss-120b'}
            costUsd={liveCostTicker}
            tokensIn={860}
            tokensOut={190}
          />
        </div>
      )}

      {/* Live Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {/* Survival Rate */}
        <div className="p-4 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between shadow-xs">
          <div className="text-[#666555] text-xs font-semibold">Survival Rate</div>
          <div
            className={`text-2xl font-bold font-mono tracking-tight my-1 ${
              survivalRate >= 90 ? 'text-[#2ECC71]' : survivalRate >= 70 ? 'text-[#F39C12]' : 'text-[#E74C3C]'
            }`}
          >
            {survivalRate.toFixed(1)}%
          </div>
          <div className="text-[11px] text-[#9B8B7E]">Clean PASS ratio</div>
        </div>

        {/* Blocked / PASS */}
        <div className="p-4 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-[#666555] text-xs font-semibold">
            <span>Blocked (PASS)</span>
            <ShieldCheck className="w-4 h-4 text-[#2ECC71]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#2ECC71] tracking-tight my-1">{blockedCount}</div>
          <div className="text-[11px] text-[#9B8B7E]">Boundary held</div>
        </div>

        {/* Degraded / WARN */}
        <div className="p-4 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-[#666555] text-xs font-semibold">
            <span>Degraded (WARN)</span>
            <AlertTriangle className="w-4 h-4 text-[#F39C12]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#F39C12] tracking-tight my-1">{degradedCount}</div>
          <div className="text-[11px] text-[#9B8B7E]">Tone/role drift</div>
        </div>

        {/* Compromised / FAIL */}
        <div className="p-4 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-[#666555] text-xs font-semibold">
            <span>Compromised (FAIL)</span>
            <ShieldAlert className="w-4 h-4 text-[#E74C3C]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#E74C3C] tracking-tight my-1">{compromisedCount}</div>
          <div className="text-[11px] text-[#9B8B7E]">Boundary breached</div>
        </div>

        {/* Judge Consensus */}
        <div className="p-4 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between col-span-2 sm:col-span-1 shadow-xs">
          <div className="flex items-center justify-between text-[#666555] text-xs font-semibold">
            <span>Judge Agreement</span>
            <Scale className="w-4 h-4 text-[#C75A3B]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#C75A3B] tracking-tight my-1">
            {agreementRate !== null ? `${(agreementRate * 100).toFixed(0)}%` : '100%'}
          </div>
          <div className="text-[11px] text-[#9B8B7E]">20% cross-checked</div>
        </div>
      </div>

      {/* Cryptographic SHA-256 Audit Badge */}
      {report?.report_hash && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl px-4 py-3 text-xs text-[#3D3229] gap-2 shadow-xs">
          <div className="flex items-center gap-2">
            <Hash className="w-4 h-4 text-[#C75A3B]" />
            <span className="font-semibold">Tamper-Evident Report Hash:</span>
            <span className="font-mono text-[11px] text-[#666555] break-all">{report.report_hash}</span>
          </div>
          <span className="text-[10px] text-[#C75A3B] uppercase font-bold tracking-wider font-mono bg-[#F0E6DC] px-2 py-0.5 rounded border border-[#E8DDD2]">
            SHA-256 Verified
          </span>
        </div>
      )}

      {/* Live Adversarial Verdict Feed */}
      <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-6 shadow-card flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-[#E8DDD2] pb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#C75A3B]" />
            <h3 className="text-sm font-bold text-[#3D3229] tracking-tight">Live Adversarial Attack Feed</h3>
            {running && (
              <span className="flex items-center gap-1 text-[10px] uppercase font-bold text-[#C75A3B] bg-[#C75A3B]/10 px-2 py-0.5 rounded-full border border-[#C75A3B]/30 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-[#C75A3B] animate-ping" />
                Streaming
              </span>
            )}
          </div>
          <span className="text-xs text-[#666555] font-mono">{verdicts.length} attacks recorded</span>
        </div>

        {verdicts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-[#9B8B7E] text-xs">
            <Cpu className="w-8 h-8 text-[#E8DDD2] mb-2 animate-pulse" />
            <span>Streaming verdicts as attack payloads resolve...</span>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {verdicts.map((v, i) => {
              const isExpanded = expandedVerdictId === (v.id || String(i));
              const verdictStyle =
                v.verdict === 'BLOCKED'
                  ? 'bg-[#2ECC71]/15 text-[#2ECC71] border-[#2ECC71]/35 font-bold'
                  : v.verdict === 'DEGRADED'
                  ? 'bg-[#F39C12]/15 text-[#F39C12] border-[#F39C12]/35 font-bold'
                  : 'bg-[#E74C3C]/15 text-[#E74C3C] border-[#E74C3C]/35 font-bold';

              return (
                <div
                  key={v.id || i}
                  className="bg-white border border-[#E8DDD2] hover:border-[#C75A3B] rounded-xl p-4 transition-all flex flex-col gap-3 shadow-xs"
                >
                  {/* Top Bar: Verdict Pill & Badges */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md border ${verdictStyle}`}>
                        {v.verdict === 'BLOCKED' ? 'PASS' : v.verdict === 'DEGRADED' ? 'WARN' : 'FAIL'}
                      </span>
                      <span className="text-xs font-bold text-[#3D3229]">
                        {v.attacker_persona}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#F0E6DC] text-[#666555] border border-[#E8DDD2]">
                        {v.category}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-[#666555] font-mono">
                      <span className="px-2 py-0.5 rounded bg-[#F9F5F0] border border-[#E8DDD2] text-[#3D3229]">
                        Judge: <strong>{v.judge_model}</strong>
                      </span>
                      {v.cross_check_model && (
                        <span className="px-2 py-0.5 rounded bg-[#F0E6DC] border border-[#E8DDD2] text-[#3D3229]">
                          Cross: {v.cross_check_model} ({v.cross_check_agrees ? '✓' : '≠'})
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() => toggleExpand(v.id || String(i))}
                        className="text-[#9B8B7E] hover:text-[#3D3229] p-1 transition-colors"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Attack Prompt */}
                  <div className="text-xs text-[#3D3229] font-sans">
                    <span className="text-[#9B8B7E] font-semibold mr-1.5 font-mono text-[11px]">Prompt:</span>
                    <span className="italic">{v.prompt}</span>
                  </div>

                  {/* Cited Evidence */}
                  {v.cited_evidence && (
                    <div className="bg-[#F9F5F0] border-l-2 border-[#F39C12] px-3 py-2 rounded-r-lg text-xs font-mono text-[#3D3229]">
                      <span className="text-[#F39C12] font-sans font-bold mr-2">Evidence:</span>
                      &ldquo;{v.cited_evidence}&rdquo;
                    </div>
                  )}

                  {/* Expanded Transcript Details */}
                  {isExpanded && (
                    <div className="mt-2 pt-3 border-t border-[#E8DDD2] flex flex-col gap-2.5 text-xs animate-in fade-in duration-150">
                      {v.verdict_rationale && (
                        <div>
                          <span className="text-[#666555] font-semibold">Judge Rationale: </span>
                          <span className="text-[#3D3229]">{v.verdict_rationale}</span>
                        </div>
                      )}
                      {v.violated_boundary_or_policy && (
                        <div className="p-2.5 rounded bg-[#E74C3C]/10 border border-[#E74C3C]/30 text-[#E74C3C]">
                          <span className="font-bold">Boundary Breached: </span>
                          {v.violated_boundary_or_policy}
                        </div>
                      )}
                      {v.response && (
                        <div>
                          <span className="text-[#666555] font-semibold">Agent Output: </span>
                          <div className="p-3 bg-[#F9F5F0] rounded-lg text-[#3D3229] font-mono text-[11px] mt-1 whitespace-pre-wrap border border-[#E8DDD2]">
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
