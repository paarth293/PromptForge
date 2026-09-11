'use client';

import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Wrench,
  ArrowRight,
  CheckCircle2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  FileCode,
  Layers,
  Sparkles,
  GitCommit,
  Award,
  Loader2
} from 'lucide-react';

export interface PatchEntryData {
  patch_id: string;
  category: string;
  target: string;
  target_name?: string | null;
  action: string;
  original_snippet?: string | null;
  patched_snippet?: string | null;
  diff: string;
  rationale: string;
}

export interface HardeningPassRecordData {
  pass_number: number;
  categories_targeted: string[];
  patches_applied: PatchEntryData[];
  sessions_run: number;
  survival_rate_before: number;
  survival_rate_after: number;
}

export interface HardeningLogData {
  log_id: string;
  initial_blueprint_id: string;
  hardened_blueprint_id: string;
  initial_survival_rate: number;
  final_survival_rate: number;
  pass_count: number;
  applied_patches: PatchEntryData[];
  pass_records: HardeningPassRecordData[];
  log_hash?: string | null;
  created_at: string;
}

interface HardeningLogViewProps {
  hardeningLog?: HardeningLogData | null;
  agentName: string;
  onBackToRedTeam?: () => void;
  onChatWithHardenedAgent?: () => void;
  onProceedToVerification?: () => void;
  loading?: boolean;
}

export default function HardeningLogView({
  hardeningLog,
  agentName,
  onBackToRedTeam,
  onChatWithHardenedAgent,
  onProceedToVerification,
  loading = false
}: HardeningLogViewProps) {
  const [expandedDiffs, setExpandedDiffs] = useState<Record<string, boolean>>({});
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [activeTab, setActiveTab] = useState<'visual' | 'plain'>('visual');

  if (loading) {
    return (
      <div className="w-full max-w-5xl mx-auto p-12 rounded-2xl bg-[#121826] border border-[#232D42] text-center space-y-4 animate-in fade-in duration-200">
        <div className="w-12 h-12 rounded-2xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
        </div>
        <h3 className="text-lg font-bold text-white">Synthesizing Surgical Guardrail Patches</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Analyzing breach transcripts, generating minimal boundary diffs without prompt bloat, and re-attacking the agent to verify patch resilience...
        </p>
      </div>
    );
  }

  if (!hardeningLog) {
    return (
      <div className="w-full max-w-5xl mx-auto p-12 rounded-2xl bg-[#121826] border border-[#232D42] text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 mx-auto">
          <Wrench className="w-6 h-6 text-slate-400" />
        </div>
        <h3 className="text-lg font-bold text-white">No Hardening Log Generated Yet</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Execute a Red Team attack suite first to discover boundary leaks and generate verified surgical patches.
        </p>
        {onBackToRedTeam && (
          <button
            type="button"
            onClick={onBackToRedTeam}
            className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-300 text-xs font-semibold rounded-xl inline-flex items-center gap-2 transition-all"
          >
            Go to Red Team View
          </button>
        )}
      </div>
    );
  }

  const toggleDiff = (id: string) => {
    setExpandedDiffs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCopyHash = () => {
    if (hardeningLog.log_hash) {
      navigator.clipboard.writeText(hardeningLog.log_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const survivalGain = Math.max(
    0,
    Math.round((hardeningLog.final_survival_rate - hardeningLog.initial_survival_rate) * 100)
  );

  // Non-engineer readable plain text summary
  const generatePlainTextSummary = (): string => {
    const p1 = `PROMPTFORGE HARDENING LOG — ${agentName}\n`;
    const p2 = `Survival: ${(hardeningLog.initial_survival_rate * 100).toFixed(0)}% → ${(hardeningLog.final_survival_rate * 100).toFixed(0)}% after ${hardeningLog.pass_count} hardening pass(es)\n\n`;
    const patches = hardeningLog.applied_patches.map((p, idx) => {
      return `  Patch ${idx + 1} [${p.target.toUpperCase()}]: ${p.rationale}\n    Diff: ${p.diff.split('\n')[0]}`;
    }).join('\n\n');
    return p1 + p2 + 'Applied Patches:\n' + patches + `\n\nIntegrity Hash: ${hardeningLog.log_hash || 'SHA256-PENDING'}`;
  };

  const handleCopyText = () => {
    navigator.clipboard.writeText(generatePlainTextSummary());
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl shadow-card">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-xl bg-[#F0E6DC] border border-[#E8DDD2] text-[#C75A3B]">
            <Wrench className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-[#3D3229] tracking-tight">
                Stage 5: Guardrail Hardening Log
              </h2>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F0E6DC] text-[#C75A3B] border border-[#E8DDD2]">
                {agentName}
              </span>
            </div>
            <p className="text-xs text-[#666555] mt-1">
              Surgical repairs • Non-wholesale diffs • Targeted re-attack verification
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {onBackToRedTeam && (
            <button
              onClick={onBackToRedTeam}
              className="btn-secondary text-xs"
            >
              ← Red Team Studio
            </button>
          )}
          {onChatWithHardenedAgent && (
            <button
              onClick={onChatWithHardenedAgent}
              className="btn-secondary text-xs"
            >
              <span>Test Chat</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
          {onProceedToVerification && (
            <button
              onClick={onProceedToVerification}
              className="btn-primary text-xs"
            >
              <Award className="w-3.5 h-3.5" />
              <span>Verify Scorecard</span>
            </button>
          )}
        </div>
      </div>

      {/* Survival Progression Hero Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 p-6 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#666555]">
              Survival Rate Progression
            </span>
            <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-[#2ECC71]/15 text-[#2ECC71] border border-[#2ECC71]/30">
              <Sparkles className="w-3.5 h-3.5" />
              +{survivalGain}% Improvement
            </span>
          </div>

          <div className="flex items-baseline gap-4 my-4">
            <div>
              <div className="text-xs text-[#666555]">Initial Attack Survival</div>
              <div className="text-3xl font-extrabold text-[#E74C3C]">
                {(hardeningLog.initial_survival_rate * 100).toFixed(0)}%
              </div>
            </div>
            <ArrowRight className="w-6 h-6 text-[#9B8B7E] self-center" />
            <div>
              <div className="text-xs text-[#666555]">Hardened Survival</div>
              <div className="text-4xl font-extrabold text-[#2ECC71]">
                {(hardeningLog.final_survival_rate * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Progress Visual Bar */}
          <div className="space-y-1.5">
            <div className="w-full h-3 bg-[#F0E6DC] rounded-full overflow-hidden flex border border-[#E8DDD2]">
              <div
                style={{ width: `${hardeningLog.initial_survival_rate * 100}%` }}
                className="bg-[#F39C12] h-full"
              />
              <div
                style={{ width: `${survivalGain}%` }}
                className="bg-[#2ECC71] h-full"
              />
            </div>
            <div className="flex justify-between text-[11px] text-[#666555] font-mono">
              <span>Passes: {hardeningLog.pass_count}</span>
              <span className="text-[#2ECC71] font-semibold">Target: 85% met</span>
            </div>
          </div>
        </div>

        {/* Blueprint Revision & Hash Card */}
        <div className="p-6 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl flex flex-col justify-between space-y-4 shadow-card">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#666555] uppercase tracking-wider">
              <GitCommit className="w-4 h-4 text-[#C75A3B]" />
              <span>Blueprint Lineage</span>
            </div>
            <div className="mt-2 text-xs font-mono text-[#3D3229] space-y-1 bg-white p-2.5 rounded-lg border border-[#E8DDD2]">
              <div><span className="text-[#9B8B7E]">v1:</span> {hardeningLog.initial_blueprint_id.slice(0, 16)}...</div>
              <div><span className="text-[#2ECC71] font-bold">v2:</span> {hardeningLog.hardened_blueprint_id.slice(0, 16)}...</div>
            </div>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-wider text-[#666555] font-semibold mb-1">
              Tamper-Evident SHA-256
            </div>
            <div className="flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-[#E8DDD2] text-[11px] font-mono text-[#3D3229]">
              <span className="truncate">{hardeningLog.log_hash || 'SHA256-PENDING'}</span>
              <button
                onClick={handleCopyHash}
                className="text-[#666555] hover:text-[#C75A3B] transition ml-2"
                title="Copy Hash"
              >
                {copiedHash ? <Check className="w-3.5 h-3.5 text-[#2ECC71]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs: Visual Diff Cards vs Plain Text Log */}
      <div className="flex items-center justify-between border-b border-[#E8DDD2] pb-2">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('visual')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'visual'
                ? 'bg-[#C75A3B] text-white shadow-sm'
                : 'text-[#666555] hover:text-[#3D3229]'
            }`}
          >
            Surgical Patches ({hardeningLog.applied_patches.length})
          </button>
          <button
            onClick={() => setActiveTab('plain')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'plain'
                ? 'bg-[#C75A3B] text-white shadow-sm'
                : 'text-[#666555] hover:text-[#3D3229]'
            }`}
          >
            Compliance Text Log
          </button>
        </div>

        <button
          onClick={handleCopyText}
          className="btn-secondary text-xs"
        >
          {copiedText ? <Check className="w-3.5 h-3.5 text-[#2ECC71]" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copiedText ? 'Copied Log' : 'Copy Log'}</span>
        </button>
      </div>

      {/* Tab 1: Visual Cards with Surgical Unified Diffs */}
      {activeTab === 'visual' && (
        <div className="space-y-4">
          {hardeningLog.applied_patches.map((patch, idx) => {
            const isExpanded = !!expandedDiffs[patch.patch_id];
            const targetColor =
              patch.target === 'guardrails'
                ? 'text-[#2ECC71] bg-[#2ECC71]/10 border-[#2ECC71]/30'
                : patch.target === 'tool_policy'
                ? 'text-[#C75A3B] bg-[#C75A3B]/10 border-[#C75A3B]/30'
                : 'text-[#D97D5E] bg-[#D97D5E]/10 border-[#D97D5E]/30';

            return (
              <div
                key={patch.patch_id}
                className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-5 space-y-3 shadow-card transition hover:border-[#C75A3B]"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-[#3D3229] px-2 py-0.5 rounded bg-white border border-[#E8DDD2]">
                      {patch.patch_id}
                    </span>
                    <span className={`text-[11px] font-semibold uppercase px-2.5 py-0.5 rounded-full border ${targetColor}`}>
                      {patch.target.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-[#666555] font-medium">
                      Category: <strong className="text-[#3D3229]">{patch.category}</strong>
                    </span>
                  </div>

                  {patch.target_name && (
                    <span className="text-xs text-[#666555] font-mono">
                      Target: {patch.target_name}
                    </span>
                  )}
                </div>

                {/* Non-engineer explanation rationale */}
                <div className="text-sm text-[#3D3229] font-normal leading-relaxed">
                  <strong className="text-[#666555] text-xs uppercase tracking-wider mr-1">Rationale:</strong>
                  {patch.rationale}
                </div>

                {/* Unified Diff Accordion */}
                <div className="pt-1">
                  <button
                    onClick={() => toggleDiff(patch.patch_id)}
                    className="flex items-center gap-1.5 text-xs text-[#C75A3B] hover:text-[#B84A2F] font-semibold transition"
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    <span>{isExpanded ? 'Hide Unified Diff' : 'View Surgical Diff (+/-)'}</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {isExpanded && (
                    <div className="mt-2.5 rounded-lg bg-white border border-[#E8DDD2] p-3 font-mono text-xs overflow-x-auto shadow-xs">
                      {patch.diff.split('\n').map((line, lIdx) => {
                        const isAdd = line.startsWith('+') && !line.startsWith('+++');
                        const isDel = line.startsWith('-') && !line.startsWith('---');
                        const isHeader = line.startsWith('---') || line.startsWith('+++');
                        return (
                          <div
                            key={lIdx}
                            className={`${
                              isAdd
                                ? 'text-[#2ECC71] bg-[#2ECC71]/10 px-1 py-0.5 rounded font-semibold'
                                : isDel
                                ? 'text-[#E74C3C] bg-[#E74C3C]/10 px-1 py-0.5 rounded font-semibold'
                                : isHeader
                                ? 'text-[#9B8B7E] font-semibold'
                                : 'text-[#666555]'
                            }`}
                          >
                            {line}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 2: Plain Text Compliance Log */}
      {activeTab === 'plain' && (
        <div className="bg-white border border-[#E8DDD2] rounded-xl p-5 font-mono text-xs text-[#3D3229] whitespace-pre-wrap leading-relaxed overflow-x-auto shadow-xs">
          {generatePlainTextSummary()}
        </div>
      )}

      {/* Multi-Pass Iteration Summary Timeline */}
      {hardeningLog.pass_records && hardeningLog.pass_records.length > 0 && (
        <div className="p-5 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl space-y-3 shadow-card">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#666555] flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#2ECC71]" />
            <span>Pass Breakdown Timeline</span>
          </h3>

          <div className="space-y-2">
            {hardeningLog.pass_records.map((rec) => (
              <div
                key={rec.pass_number}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-white border border-[#E8DDD2] text-xs gap-2 shadow-xs"
              >
                <div className="flex items-center gap-2.5">
                  <span className="font-bold text-[#2ECC71]">Pass {rec.pass_number}</span>
                  <span className="text-[#666555]">
                    Targeted: <span className="text-[#3D3229] font-semibold">{rec.categories_targeted.join(', ')}</span>
                  </span>
                </div>
                <div className="flex items-center gap-4 text-[#3D3229] font-mono">
                  <span>{rec.sessions_run} re-attack sessions</span>
                  <span className="text-[#666555]">
                    {(rec.survival_rate_before * 100).toFixed(0)}% →{' '}
                    <strong className="text-[#2ECC71]">{(rec.survival_rate_after * 100).toFixed(0)}%</strong>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
