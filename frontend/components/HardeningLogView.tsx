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
  Award
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
  hardeningLog: HardeningLogData;
  agentName: string;
  onBackToRedTeam?: () => void;
  onChatWithHardenedAgent?: () => void;
  onProceedToVerification?: () => void;
}

export default function HardeningLogView({
  hardeningLog,
  agentName,
  onBackToRedTeam,
  onChatWithHardenedAgent,
  onProceedToVerification
}: HardeningLogViewProps) {
  const [expandedDiffs, setExpandedDiffs] = useState<Record<string, boolean>>({});
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [activeTab, setActiveTab] = useState<'visual' | 'plain'>('visual');

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
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 bg-[#111726] border border-[#232D42] rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Wrench className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white tracking-tight">
                Stage 2.5: Guardrail Hardening Log
              </h2>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {agentName}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Surgical repairs • Non-wholesale diffs • Targeted re-attack verification
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onBackToRedTeam && (
            <button
              onClick={onBackToRedTeam}
              className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              ← Red Team View
            </button>
          )}
          {onChatWithHardenedAgent && (
            <button
              onClick={onChatWithHardenedAgent}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <span>Test Chat</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
          {onProceedToVerification && (
            <button
              onClick={onProceedToVerification}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20 transition"
            >
              <Award className="w-3.5 h-3.5" />
              <span>Verify Scorecard</span>
            </button>
          )}
        </div>
      </div>

      {/* Survival Progression Hero Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 p-6 bg-[#151C2C] border border-[#232D42] rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Survival Rate Progression
            </span>
            <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              <Sparkles className="w-3.5 h-3.5" />
              +{survivalGain}% Improvement
            </span>
          </div>

          <div className="flex items-baseline gap-4 my-4">
            <div>
              <div className="text-xs text-slate-400">Initial Attack Survival</div>
              <div className="text-3xl font-extrabold text-red-400">
                {(hardeningLog.initial_survival_rate * 100).toFixed(0)}%
              </div>
            </div>
            <ArrowRight className="w-6 h-6 text-slate-500 self-center" />
            <div>
              <div className="text-xs text-slate-400">Hardened Survival</div>
              <div className="text-4xl font-extrabold text-emerald-400">
                {(hardeningLog.final_survival_rate * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          {/* Progress Visual Bar */}
          <div className="space-y-1.5">
            <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden flex">
              <div
                style={{ width: `${hardeningLog.initial_survival_rate * 100}%` }}
                className="bg-amber-500 h-full"
              />
              <div
                style={{ width: `${survivalGain}%` }}
                className="bg-emerald-500 h-full animate-pulse"
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span>Passes: {hardeningLog.pass_count}</span>
              <span>Target: 85% met</span>
            </div>
          </div>
        </div>

        {/* Blueprint Revision & Hash Card */}
        <div className="p-6 bg-[#151C2C] border border-[#232D42] rounded-2xl flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <GitCommit className="w-4 h-4 text-blue-400" />
              <span>Blueprint Lineage</span>
            </div>
            <div className="mt-2 text-xs font-mono text-slate-300 space-y-1 bg-black/40 p-2.5 rounded-lg border border-slate-800">
              <div><span className="text-slate-500">v1:</span> {hardeningLog.initial_blueprint_id.slice(0, 16)}...</div>
              <div><span className="text-emerald-400">v2:</span> {hardeningLog.hardened_blueprint_id.slice(0, 16)}...</div>
            </div>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-1">
              Tamper-Evident SHA-256
            </div>
            <div className="flex items-center justify-between bg-black/40 px-3 py-2 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300">
              <span className="truncate">{hardeningLog.log_hash || 'SHA256-PENDING'}</span>
              <button
                onClick={handleCopyHash}
                className="text-slate-400 hover:text-white transition ml-2"
                title="Copy Hash"
              >
                {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs: Visual Diff Cards vs Plain Text Log */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('visual')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'visual'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Surgical Patches ({hardeningLog.applied_patches.length})
          </button>
          <button
            onClick={() => setActiveTab('plain')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'plain'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Compliance Text Log
          </button>
        </div>

        <button
          onClick={handleCopyText}
          className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
        >
          {copiedText ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
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
                ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                : patch.target === 'tool_policy'
                ? 'text-purple-400 bg-purple-500/10 border-purple-500/30'
                : 'text-blue-400 bg-blue-500/10 border-blue-500/30';

            return (
              <div
                key={patch.patch_id}
                className="bg-[#151C2C] border border-[#232D42] rounded-xl p-5 space-y-3 transition hover:border-slate-600"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-slate-300 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                      {patch.patch_id}
                    </span>
                    <span className={`text-[11px] font-semibold uppercase px-2.5 py-0.5 rounded-full border ${targetColor}`}>
                      {patch.target.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">
                      Category: <strong className="text-slate-200">{patch.category}</strong>
                    </span>
                  </div>

                  {patch.target_name && (
                    <span className="text-xs text-slate-400 font-mono">
                      Target: {patch.target_name}
                    </span>
                  )}
                </div>

                {/* Non-engineer explanation rationale */}
                <div className="text-sm text-slate-200 font-normal leading-relaxed">
                  <strong className="text-slate-400 text-xs uppercase tracking-wider mr-1">Rationale:</strong>
                  {patch.rationale}
                </div>

                {/* Unified Diff Accordion */}
                <div className="pt-1">
                  <button
                    onClick={() => toggleDiff(patch.patch_id)}
                    className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-medium transition"
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    <span>{isExpanded ? 'Hide Unified Diff' : 'View Surgical Diff (+/-)'}</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {isExpanded && (
                    <div className="mt-2.5 rounded-lg bg-[#0B0F19] border border-slate-800 p-3 font-mono text-xs overflow-x-auto">
                      {patch.diff.split('\n').map((line, lIdx) => {
                        const isAdd = line.startsWith('+') && !line.startsWith('+++');
                        const isDel = line.startsWith('-') && !line.startsWith('---');
                        const isHeader = line.startsWith('---') || line.startsWith('+++');
                        return (
                          <div
                            key={lIdx}
                            className={`${
                              isAdd
                                ? 'text-emerald-400 bg-emerald-500/10 px-1 py-0.5 rounded'
                                : isDel
                                ? 'text-red-400 bg-red-500/10 px-1 py-0.5 rounded'
                                : isHeader
                                ? 'text-slate-500 font-semibold'
                                : 'text-slate-400'
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
        <div className="bg-[#0B0F19] border border-slate-800 rounded-xl p-5 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
          {generatePlainTextSummary()}
        </div>
      )}

      {/* Multi-Pass Iteration Summary Timeline */}
      {hardeningLog.pass_records && hardeningLog.pass_records.length > 0 && (
        <div className="p-5 bg-[#151C2C] border border-[#232D42] rounded-xl space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <span>Pass Breakdown Timeline</span>
          </h3>

          <div className="space-y-2">
            {hardeningLog.pass_records.map((rec) => (
              <div
                key={rec.pass_number}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-black/40 border border-slate-800 text-xs gap-2"
              >
                <div className="flex items-center gap-2.5">
                  <span className="font-bold text-emerald-400">Pass {rec.pass_number}</span>
                  <span className="text-slate-400">
                    Targeted: <span className="text-slate-200">{rec.categories_targeted.join(', ')}</span>
                  </span>
                </div>
                <div className="flex items-center gap-4 text-slate-300 font-mono">
                  <span>{rec.sessions_run} re-attack sessions</span>
                  <span className="text-slate-400">
                    {(rec.survival_rate_before * 100).toFixed(0)}% →{' '}
                    <strong className="text-emerald-400">{(rec.survival_rate_after * 100).toFixed(0)}%</strong>
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
