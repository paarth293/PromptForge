'use client';

import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Award,
  Hash,
  Calculator,
  Terminal,
  Copy,
  Check,
  ArrowLeft,
  RotateCw,
  FileText,
  Sparkles,
  Layers,
  Scale,
  Loader2
} from 'lucide-react';

export interface VerificationScorecardData {
  scorecard_id: string;
  blueprint_id: string;
  agent_name: string;
  birth_certificate_hash?: string | null;
  user_gold_score?: [number, number] | null;
  generated_set_score: [number, number];
  goal_completion_score: [number, number];
  consistency_score: [number, number];
  adversarial_survival_score: [number, number];
  judge_cross_check?: [number, number] | null;
  alignment_audit_score: number;
  category_breakdown?: Record<string, string> | null;
  difficulty_mix?: string | null;
  promptforge_composite_score: number;
  formula_disclosed: string;
  scorecard_hash?: string | null;
  created_at: string;
}

interface VerificationScorecardViewProps {
  scorecard?: VerificationScorecardData | null;
  agentName?: string;
  onBackToChat?: () => void;
  onBackToHardening?: () => void;
  onRerunVerify?: () => void;
  loading?: boolean;
}

export default function VerificationScorecardView({
  scorecard,
  agentName = 'Agent',
  onBackToChat,
  onBackToHardening,
  onRerunVerify,
  loading = false
}: VerificationScorecardViewProps) {
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedAscii, setCopiedAscii] = useState(false);
  const [showAsciiView, setShowAsciiView] = useState(false);

  if (loading) {
    return (
      <div className="w-full max-w-5xl mx-auto p-12 rounded-2xl bg-[#121826] border border-[#232D42] text-center space-y-4 animate-in fade-in duration-200">
        <div className="w-12 h-12 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mx-auto">
          <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
        </div>
        <h3 className="text-lg font-bold text-white">Running Multi-Stage Verification Battery</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Evaluating ground-truth exact accuracy, tool-call sequence consistency across 5 runs, multi-turn goal journeys, and black-box alignment...
        </p>
      </div>
    );
  }

  if (!scorecard) {
    return (
      <div className="w-full max-w-5xl mx-auto p-12 rounded-2xl bg-[#121826] border border-[#232D42] text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 mx-auto">
          <Award className="w-6 h-6 text-slate-400" />
        </div>
        <h3 className="text-lg font-bold text-white">No Verification Scorecard Generated Yet</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Run the full 7-metric verification battery to evaluate {agentName}&apos;s accuracy, consistency, and alignment against the confirmed specification.
        </p>
        {onRerunVerify && (
          <button
            type="button"
            onClick={onRerunVerify}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-500/20 transition-all inline-flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Run Verification Battery Now
          </button>
        )}
      </div>
    );
  }

  const composite = scorecard.promptforge_composite_score;
  const isHighPassing = composite >= 90;
  const isPassing = composite >= 80;

  const handleCopyHash = () => {
    if (scorecard.scorecard_hash) {
      navigator.clipboard.writeText(scorecard.scorecard_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const generateAsciiCard = () => {
    const bcTag = scorecard.birth_certificate_hash
      ? `Birth Certificate: ${scorecard.birth_certificate_hash.slice(0, 8)}…${scorecard.birth_certificate_hash.slice(-2)}`
      : `Hash: ${scorecard.scorecard_hash?.slice(0, 8)}…`;
    const lines = [
      `PROMPTFORGE SCORECARD — "${scorecard.agent_name || agentName}"   (${bcTag})`,
      '────────────────────────────────────────────────────────────────────'
    ];

    if (scorecard.user_gold_score) {
      const ugStr = `${scorecard.user_gold_score[0]}/${scorecard.user_gold_score[1]}`;
      lines.push(`${'User-gold accuracy'.padEnd(28)} ${ugStr.padEnd(6)} your cases, exact-scored        weight 20%`);
    }
    const genWeight = scorecard.user_gold_score ? 'weight 20%' : 'weight 40%';
    const genStr = `${scorecard.generated_set_score[0]}/${scorecard.generated_set_score[1]}`;
    lines.push(`${'Generated-set accuracy'.padEnd(28)} ${genStr.padEnd(6)} independent edge cases          ${genWeight}`);

    const goalStr = `${scorecard.goal_completion_score[0]}/${scorecard.goal_completion_score[1]}`;
    lines.push(`${'Goal completion'.padEnd(28)} ${goalStr.padEnd(6)} simulated-customer journeys     weight 25%`);

    const conStr = `${scorecard.consistency_score[0]}/${scorecard.consistency_score[1]}`;
    lines.push(`${'Tool-usage consistency'.padEnd(28)} ${conStr.padEnd(6)} same tool calls across 5 runs   weight 15%`);

    const advStr = `${scorecard.adversarial_survival_score[0]}/${scorecard.adversarial_survival_score[1]}`;
    lines.push(`${'Adversarial survival'.padEnd(28)} ${advStr.padEnd(6)} after hardening                 weight 20%`);

    if (scorecard.category_breakdown) {
      const cats = Object.entries(scorecard.category_breakdown)
        .map(([k, v]) => `${k} ${v}`)
        .join(' │ ');
      lines.push(`   ${cats}`);
    }

    if (scorecard.difficulty_mix) {
      lines.push(`   difficulty mix: ${scorecard.difficulty_mix}`);
    }

    if (scorecard.judge_cross_check) {
      const jStr = `${scorecard.judge_cross_check[0]}/${scorecard.judge_cross_check[1]}`;
      lines.push(`${'Judge cross-check'.padEnd(28)} ${jStr.padEnd(6)} third-model agreement, disclosed`);
    }

    lines.push(`${'Alignment audit score'.padEnd(28)} ${(scorecard.alignment_audit_score * 100).toFixed(1)}%  spec-inference fidelity`);
    lines.push(`${'PromptForge Score'.padEnd(28)} ${scorecard.promptforge_composite_score}/100   ${scorecard.formula_disclosed}`);
    lines.push('Sample sizes: 4–20 per metric — indicative, raw counts always shown.');
    lines.push('Nothing on this card graded itself. Verify it any time via the hash chain.');

    return lines.join('\n');
  };

  const handleCopyAscii = () => {
    const text = generateAsciiCard();
    navigator.clipboard.writeText(text);
    setCopiedAscii(true);
    setTimeout(() => setCopiedAscii(false), 2000);
  };

  return (
    <div className="w-full max-w-4xl mx-auto bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-6 md:p-8 shadow-card space-y-6 text-[#3D3229]">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E8DDD2] pb-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-[#F0E6DC] border border-[#E8DDD2] flex items-center justify-center text-[#C75A3B] shadow-xs">
            <Award className="w-6 h-6 text-[#C75A3B]" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-[#3D3229] tracking-tight">
                PromptForge Verification Scorecard
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase bg-[#2ECC71]/15 text-[#2ECC71] border border-[#2ECC71]/30 font-bold">
                Non-Circular Audit
              </span>
            </div>
            <p className="text-xs text-[#666555] mt-0.5">
              Target Agent: <strong className="text-[#3D3229]">{scorecard.agent_name || agentName}</strong> • Five empirical dimensions, zero self-assessment
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowAsciiView(!showAsciiView)}
            className="btn-secondary text-xs"
            title="Toggle terminal ASCII layout"
          >
            <Terminal className="w-3.5 h-3.5 text-[#C75A3B]" />
            {showAsciiView ? 'Dashboard View' : 'Appendix E ASCII'}
          </button>
          {onRerunVerify && (
            <button
              onClick={onRerunVerify}
              disabled={loading}
              className="btn-primary text-xs"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Re-Verify
            </button>
          )}
        </div>
      </div>

      {/* Main Score Hero */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-white border border-[#E8DDD2] rounded-xl p-5 shadow-xs">
        <div className="flex flex-col items-center justify-center text-center p-4 bg-[#F9F5F0] rounded-xl border border-[#E8DDD2]">
          <span className="text-xs uppercase font-mono tracking-wider text-[#666555] mb-1 font-semibold">
            PromptForge Score
          </span>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-5xl font-black font-mono tracking-tight ${
                isHighPassing
                  ? 'text-[#2ECC71]'
                  : isPassing
                  ? 'text-[#C75A3B]'
                  : 'text-[#F39C12]'
              }`}
            >
              {composite}
            </span>
            <span className="text-[#9B8B7E] text-xl font-mono">/100</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px] font-semibold text-[#2ECC71] bg-[#2ECC71]/15 px-2.5 py-1 rounded-full border border-[#2ECC71]/30">
            <ShieldCheck className="w-3.5 h-3.5" />
            Verified Production Ready
          </div>
        </div>

        <div className="md:col-span-2 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#3D3229] uppercase tracking-wider mb-1">
              <Calculator className="w-4 h-4 text-[#C75A3B]" />
              Disclosed Weighted Formula (Appendix E)
            </div>
            <div className="p-3 rounded-lg bg-[#F9F5F0] border border-[#E8DDD2] font-mono text-xs text-[#C75A3B] font-semibold overflow-x-auto">
              PromptForge Score {scorecard.formula_disclosed}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="flex items-center gap-2 text-xs text-[#666555]">
              <Hash className="w-3.5 h-3.5 text-[#9B8B7E]" />
              <span className="truncate">
                SHA-256 Stamp:{' '}
                <span className="font-mono text-[#3D3229] font-medium">
                  {scorecard.scorecard_hash ? `${scorecard.scorecard_hash.slice(0, 16)}…` : 'Pending'}
                </span>
              </span>
              <button
                onClick={handleCopyHash}
                className="text-[#666555] hover:text-[#C75A3B] transition-colors"
                title="Copy full cryptographic SHA-256 hash"
              >
                {copiedHash ? <Check className="w-3 h-3 text-[#2ECC71]" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs text-[#666555]">
              <Scale className="w-3.5 h-3.5 text-[#C75A3B]" />
              <span>
                Judge Cross-Check:{' '}
                <strong className="text-[#3D3229] font-mono">
                  {scorecard.judge_cross_check
                    ? `${scorecard.judge_cross_check[0]}/${scorecard.judge_cross_check[1]} Agreement`
                    : 'Disclosed Independent Model'}
                </strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ASCII View Toggle */}
      {showAsciiView ? (
        <div className="space-y-3 animate-in fade-in duration-200">
          <div className="flex items-center justify-between text-xs text-[#666555]">
            <span className="font-mono uppercase font-semibold text-[#666555]">Canonical Markdown / ASCII Terminal Output</span>
            <button
              onClick={handleCopyAscii}
              className="btn-secondary text-xs"
            >
              {copiedAscii ? <Check className="w-3.5 h-3.5 text-[#2ECC71]" /> : <Copy className="w-3.5 h-3.5" />}
              {copiedAscii ? 'Copied to Clipboard' : 'Copy ASCII'}
            </button>
          </div>
          <pre className="p-5 bg-white border border-[#E8DDD2] rounded-xl text-[#3D3229] font-mono text-xs overflow-x-auto leading-relaxed shadow-xs">
            {generateAsciiCard()}
          </pre>
        </div>
      ) : (
        /* Rich Dashboard Dimension Breakdown */
        <div className="space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#666555] flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#C75A3B]" />
              Verified Empirical Metrics (Raw Counts Disclosed)
            </h3>
            <span className="text-[11px] text-[#9B8B7E] font-mono">
              Sample sizes: 4–20 per metric — indicative
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {/* User-Gold */}
            {scorecard.user_gold_score && (
              <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] flex items-center justify-between shadow-xs">
                <div>
                  <div className="text-xs font-semibold text-[#3D3229]">User-Gold Accuracy</div>
                  <div className="text-[11px] text-[#666555] mt-0.5">Your exact business cases, exact-scored</div>
                </div>
                <div className="text-right font-mono">
                  <div className="text-base font-bold text-[#3D3229]">
                    {scorecard.user_gold_score[0]}/{scorecard.user_gold_score[1]}
                  </div>
                  <div className="text-[11px] text-[#C75A3B] font-semibold">Weight 20%</div>
                </div>
              </div>
            )}

            {/* Generated Set */}
            <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] flex items-center justify-between shadow-xs">
              <div>
                <div className="text-xs font-semibold text-[#3D3229]">Generated-Set Accuracy</div>
                <div className="text-[11px] text-[#666555] mt-0.5">Independent edge &amp; boundary cases (Chain 10)</div>
              </div>
              <div className="text-right font-mono">
                <div className="text-base font-bold text-[#3D3229]">
                  {scorecard.generated_set_score[0]}/{scorecard.generated_set_score[1]}
                </div>
                <div className="text-[11px] text-[#C75A3B] font-semibold">
                  {scorecard.user_gold_score ? 'Weight 20%' : 'Weight 40%'}
                </div>
              </div>
            </div>

            {/* Goal Completion */}
            <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] flex items-center justify-between shadow-xs">
              <div>
                <div className="text-xs font-semibold text-[#3D3229]">Goal Completion</div>
                <div className="text-[11px] text-[#666555] mt-0.5">Simulated-customer multi-turn journeys (Chain 12)</div>
              </div>
              <div className="text-right font-mono">
                <div className="text-base font-bold text-[#3D3229]">
                  {scorecard.goal_completion_score[0]}/{scorecard.goal_completion_score[1]}
                </div>
                <div className="text-[11px] text-[#C75A3B] font-semibold">Weight 25%</div>
              </div>
            </div>

            {/* Tool Consistency */}
            <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] flex items-center justify-between shadow-xs">
              <div>
                <div className="text-xs font-semibold text-[#3D3229]">Tool-Usage Consistency</div>
                <div className="text-[11px] text-[#666555] mt-0.5">Exact tool calls across 5 empirical runs (Chain 11)</div>
              </div>
              <div className="text-right font-mono">
                <div className="text-base font-bold text-[#3D3229]">
                  {scorecard.consistency_score[0]}/{scorecard.consistency_score[1]}
                </div>
                <div className="text-[11px] text-[#C75A3B] font-semibold">Weight 15%</div>
              </div>
            </div>

            {/* Adversarial Survival */}
            <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] flex items-center justify-between shadow-xs">
              <div>
                <div className="text-xs font-semibold text-[#3D3229]">Adversarial Survival</div>
                <div className="text-[11px] text-[#666555] mt-0.5">Attacks blocked after hardening (Red Team)</div>
              </div>
              <div className="text-right font-mono">
                <div className="text-base font-bold text-[#2ECC71]">
                  {scorecard.adversarial_survival_score[0]}/{scorecard.adversarial_survival_score[1]}
                </div>
                <div className="text-[11px] text-[#C75A3B] font-semibold">Weight 20%</div>
              </div>
            </div>

            {/* Spec-Inference Alignment */}
            <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] flex items-center justify-between shadow-xs">
              <div>
                <div className="text-xs font-semibold text-[#3D3229]">Alignment Audit</div>
                <div className="text-[11px] text-[#666555] mt-0.5">Black-box spec-inference fidelity vs confirmed spec</div>
              </div>
              <div className="text-right font-mono">
                <div className="text-base font-bold text-[#D97D5E]">
                  {(scorecard.alignment_audit_score * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-[#666555]">Audit Factor</div>
              </div>
            </div>
          </div>

          {/* Category Breakdown Pills */}
          {scorecard.category_breakdown && (
            <div className="p-4 rounded-xl bg-white border border-[#E8DDD2] space-y-2 shadow-xs">
              <div className="text-xs font-semibold text-[#3D3229] uppercase tracking-wider">
                Red Team Category Breakdown
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(scorecard.category_breakdown).map(([cat, res]) => (
                  <div
                    key={cat}
                    className="px-2.5 py-1 rounded-lg bg-[#F9F5F0] border border-[#E8DDD2] text-xs font-mono flex items-center gap-1.5 text-[#3D3229]"
                  >
                    <span className="capitalize">{cat}</span>
                    <span className="text-[#2ECC71] font-bold">{res}</span>
                  </div>
                ))}
              </div>
              {scorecard.difficulty_mix && (
                <div className="text-[11px] text-[#9B8B7E] font-mono pt-1">
                  Difficulty mix: {scorecard.difficulty_mix}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Footer / Navigation */}
      <div className="pt-3 border-t border-[#E8DDD2] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
        <div className="text-[#666555] flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4 text-[#2ECC71]" />
          <span>Nothing on this card graded itself. Verifiable via cryptographic hash chain.</span>
        </div>

        <div className="flex items-center gap-2.5">
          {onBackToHardening && (
            <button
              onClick={onBackToHardening}
              className="btn-secondary text-xs"
            >
              Back to Hardening
            </button>
          )}
          {onBackToChat && (
            <button
              onClick={onBackToChat}
              className="btn-primary text-xs"
            >
              <span>Chat with Verified Agent</span>
              <Sparkles className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
