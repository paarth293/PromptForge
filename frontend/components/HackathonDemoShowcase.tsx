'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Play,
  RotateCcw,
  FastForward,
  ShieldAlert,
  ShieldCheck,
  Award,
  Flame,
  DollarSign,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Layers,
  ArrowRight
} from 'lucide-react';
import { useHackathonDemo } from '../hooks/useHackathonDemo';

export default function HackathonDemoShowcase() {
  const {
    scenario,
    isDemoRunning,
    demoCompleted,
    currentStep,
    currentCost,
    visibleAttacks,
    robustnessScore,
    attackSuccessRate,
    activeTab,
    setActiveTab,
    runDemo,
    fastForwardDemo,
    resetDemo,
  } = useHackathonDemo();

  const [copiedHash, setCopiedHash] = useState(false);
  const [expandedAttackId, setExpandedAttackId] = useState<string | null>('atk-1');

  const copyCertHash = () => {
    navigator.clipboard.writeText(scenario.hardeningSummary.birthCertificateSha256);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="w-full bg-[#FBF8F4] border border-[#E8DDD2] rounded-2xl p-4 sm:p-6 md:p-8 shadow-card space-y-6">
      {/* 1. Header Bar: Title, Status, and 1-Click Action Buttons */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E8DDD2] pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#C75A3B]/10 text-[#C75A3B] border border-[#C75A3B]/25 text-xs font-bold font-mono tracking-wider">
              ⚡ HACKATHON LIVE SHOWCASE
            </span>
            <span className="text-xs font-semibold text-[#666555]">
              Sub-30s Automated Agent Hardening
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-[#3D3229] mt-1 tracking-tight">
            Stress-Testing: <span className="text-[#C75A3B]">{scenario.agentName}</span>
          </h2>
          <p className="text-xs sm:text-sm text-[#666555] max-w-2xl mt-0.5">
            Watch PromptForge execute a 15-probe adversarial cascade, surface critical privilege vulnerabilities, and patch defenses in real-time.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {!isDemoRunning && !demoCompleted && (
            <button
              onClick={runDemo}
              className="px-5 py-2.5 bg-[#C75A3B] hover:bg-[#B84A2F] text-white text-xs sm:text-sm font-bold rounded-xl shadow-brand-glow transition-all transform hover:-translate-y-0.5 flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>⚡ Run Live Demo</span>
            </button>
          )}

          {isDemoRunning && (
            <>
              <button
                disabled
                className="px-4 py-2 bg-[#C75A3B]/80 text-white text-xs font-bold rounded-xl flex items-center gap-2 cursor-wait"
              >
                <span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                <span>Simulating Attacks...</span>
              </button>
              <button
                onClick={fastForwardDemo}
                className="px-3 py-2 bg-[#F0E6DC] hover:bg-[#E8DDD2] text-[#3D3229] text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
                title="Instant finish"
              >
                <FastForward className="w-3.5 h-3.5 text-[#C75A3B]" />
                <span>Fast-Forward</span>
              </button>
            </>
          )}

          {demoCompleted && (
            <>
              <button
                onClick={runDemo}
                className="px-4 py-2 bg-[#F0E6DC] hover:bg-[#E8DDD2] text-[#3D3229] text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5 text-[#C75A3B]" />
                <span>Run Again</span>
              </button>
              <Link
                href={`/agents/${scenario.blueprint_id}`}
                target="_blank"
                className="px-4 py-2 bg-[#2ECC71] hover:bg-[#27AE60] text-white text-xs font-bold rounded-xl shadow-xs transition flex items-center gap-1.5"
              >
                <span>Live Chat Certified Agent</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </>
          )}
        </div>
      </div>

      {/* 2. Key Metrics Strip (Before vs After) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Metric 1: Robustness */}
        <div className="p-3.5 rounded-xl bg-[#F0E6DC]/60 border border-[#E8DDD2] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#666555] uppercase tracking-wider">
              Agent Robustness
            </span>
            <ShieldCheck className="w-4 h-4 text-[#2ECC71]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-[#3D3229]">{robustnessScore}%</span>
            {demoCompleted && (
              <span className="text-xs font-bold text-[#2ECC71] bg-[#2ECC71]/10 px-1.5 py-0.5 rounded">
                +54% Patched
              </span>
            )}
          </div>
          <div className="w-full h-1.5 bg-[#E8DDD2] rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#C75A3B] to-[#2ECC71] transition-all duration-700"
              style={{ width: `${robustnessScore}%` }}
            />
          </div>
        </div>

        {/* Metric 2: Attack Success Rate */}
        <div className="p-3.5 rounded-xl bg-[#F0E6DC]/60 border border-[#E8DDD2] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#666555] uppercase tracking-wider">
              Attack Success Rate
            </span>
            <ShieldAlert className="w-4 h-4 text-[#E74C3C]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-[#E74C3C]">{attackSuccessRate}%</span>
            {demoCompleted && (
              <span className="text-xs font-bold text-[#2ECC71] bg-[#2ECC71]/10 px-1.5 py-0.5 rounded">
                -54% Refused
              </span>
            )}
          </div>
          <span className="text-[11px] text-[#666555] mt-1">
            {demoCompleted ? 'Residual risk: minor DoS only' : 'High vulnerability to jailbreak'}
          </span>
        </div>

        {/* Metric 3: Live Cost Ticker */}
        <div className="p-3.5 rounded-xl bg-[#F0E6DC]/60 border border-[#E8DDD2] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#666555] uppercase tracking-wider">
              Total Run Investment
            </span>
            <DollarSign className="w-4 h-4 text-[#C75A3B]" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-mono font-black text-[#3D3229]">
              ${currentCost.toFixed(2)}
            </span>
            <span className="text-xs font-mono text-[#666555]">/ $5.00</span>
          </div>
          <div className="w-full h-1.5 bg-[#E8DDD2] rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-[#C75A3B] transition-all duration-300"
              style={{ width: `${Math.min(100, (currentCost / 5.0) * 100)}%` }}
            />
          </div>
        </div>

        {/* Metric 4: Vulnerabilities Identified */}
        <div className="p-3.5 rounded-xl bg-[#F0E6DC]/60 border border-[#E8DDD2] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#666555] uppercase tracking-wider">
              Vulnerabilities
            </span>
            <Flame className="w-4 h-4 text-[#C75A3B]" />
          </div>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-[#3D3229]">{visibleAttacks.length}</span>
            <span className="text-xs font-semibold text-[#666555]">detected</span>
          </div>
          <span className="text-[11px] font-mono text-[#C75A3B] font-bold mt-1">
            {demoCompleted ? '3 Critical • 3 High • 2 Medium' : 'Evaluating vectors...'}
          </span>
        </div>
      </div>

      {/* 3. Tab Selectors */}
      <div className="flex items-center gap-2 border-b border-[#E8DDD2] pb-2 overflow-x-auto">
        {[
          { id: 'cascade', label: '1. Attack Cascade', icon: Flame },
          { id: 'vulnerabilities', label: `2. Vulnerabilities (${visibleAttacks.length})`, icon: AlertTriangle },
          { id: 'cost', label: '3. Cost Ledger & ROI', icon: DollarSign },
          { id: 'diff', label: '4. Hardening & Certificate', icon: Award },
        ].map((tab) => {
          const active = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap ${
                active
                  ? 'bg-[#C75A3B] text-white shadow-xs'
                  : 'text-[#666555] hover:text-[#3D3229] hover:bg-[#F0E6DC]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* 4. Tab Content Panels */}
      {/* TAB 1: ATTACK CASCADE */}
      {activeTab === 'cascade' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {scenario.cascadeSteps.map((step) => {
              const isCompleted = currentStep > step.id || demoCompleted;
              const isCurrent = currentStep === step.id && isDemoRunning;
              return (
                <div
                  key={step.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isCompleted
                      ? 'bg-[#F0E6DC]/50 border-[#2ECC71]/30'
                      : isCurrent
                      ? 'bg-[#FBF8F4] border-[#C75A3B] shadow-sm ring-1 ring-[#C75A3B]/30'
                      : 'bg-[#F0E6DC]/20 border-[#E8DDD2] opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold font-mono ${
                          isCompleted
                            ? 'bg-[#2ECC71] text-white'
                            : isCurrent
                            ? 'bg-[#C75A3B] text-white animate-pulse'
                            : 'bg-[#E8DDD2] text-[#666555]'
                        }`}
                      >
                        {step.id}
                      </span>
                      <span className="text-xs font-bold text-[#3D3229]">{step.name}</span>
                    </div>
                    <span className="text-xs font-mono font-semibold text-[#666555]">
                      ${step.cost.toFixed(2)}
                    </span>
                  </div>

                  <div className="w-full h-1.5 bg-[#E8DDD2] rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        isCompleted
                          ? 'w-full bg-[#2ECC71]'
                          : isCurrent
                          ? 'w-2/3 bg-[#C75A3B] animate-pulse'
                          : 'w-0'
                      }`}
                    />
                  </div>

                  <div className="flex items-center justify-between mt-2 text-[10px] text-[#666555] font-mono">
                    <span>{isCompleted ? '✓ Verified Safe Execution' : isCurrent ? 'Active Execution...' : 'Queued'}</span>
                    <span>{isCompleted ? '100%' : isCurrent ? '65%' : '0%'}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {!demoCompleted && !isDemoRunning && (
            <div className="p-6 text-center border-2 border-dashed border-[#E8DDD2] rounded-xl bg-[#F0E6DC]/30">
              <Flame className="w-8 h-8 text-[#C75A3B] mx-auto mb-2 opacity-80" />
              <p className="text-sm font-bold text-[#3D3229]">Ready to Launch Attack Cascade</p>
              <p className="text-xs text-[#666555] mt-1 mb-4">
                Click "Run Live Demo" above to watch all 4 stages execute with real-time costs and vulnerability discovery.
              </p>
              <button
                onClick={runDemo}
                className="px-6 py-2.5 bg-[#C75A3B] hover:bg-[#B84A2F] text-white text-xs font-bold rounded-lg shadow-sm transition"
              >
                ⚡ Launch Demo Now
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: VULNERABILITY CARDS */}
      {activeTab === 'vulnerabilities' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-[#666555] px-1">
            <span>Click any vulnerability to expand the attack prompt and remedial action.</span>
            <span className="font-mono text-[#3D3229] font-bold">
              {visibleAttacks.length} / 8 Revealed
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {visibleAttacks.map((attack) => {
              const isExpanded = expandedAttackId === attack.id;
              const severityColor =
                attack.severity === 'CRITICAL'
                  ? 'bg-[#E74C3C]/10 text-[#E74C3C] border-[#E74C3C]/30'
                  : attack.severity === 'HIGH'
                  ? 'bg-[#F39C12]/10 text-[#F39C12] border-[#F39C12]/30'
                  : 'bg-[#D97D5E]/10 text-[#D97D5E] border-[#D97D5E]/30';

              return (
                <div
                  key={attack.id}
                  className="rounded-xl border border-[#E8DDD2] bg-[#FBF8F4] overflow-hidden shadow-2xs transition-all"
                >
                  <button
                    onClick={() => setExpandedAttackId(isExpanded ? null : attack.id)}
                    className="w-full text-left p-3 sm:p-4 flex items-center justify-between gap-3 hover:bg-[#F0E6DC]/40 transition"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border shrink-0 ${severityColor}`}>
                        {attack.severity}
                      </span>
                      <span className="text-xs sm:text-sm font-bold text-[#3D3229] truncate">
                        {attack.name}
                      </span>
                      <span className="hidden sm:inline text-[11px] text-[#666555] font-mono">
                        ({attack.layer})
                      </span>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs font-mono font-semibold text-[#2ECC71]">
                        {attack.confidence}% Confidence
                      </span>
                      <ChevronRight
                        className={`w-4 h-4 text-[#666555] transition-transform ${
                          isExpanded ? 'rotate-90' : ''
                        }`}
                      />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="p-4 border-t border-[#E8DDD2] bg-[#F0E6DC]/30 space-y-3 text-xs">
                      <div>
                        <span className="font-bold text-[#3D3229] block mb-1">Adversarial Prompt Payload:</span>
                        <div className="p-2.5 rounded-lg bg-[#3D3229] text-[#FBF8F4] font-mono text-[11px] select-all overflow-x-auto">
                          {attack.attack_prompt}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                        <div className="p-3 rounded-lg bg-[#FBF8F4] border border-[#E8DDD2]">
                          <span className="font-bold text-[#E74C3C] block mb-1">Vulnerability Finding:</span>
                          <p className="text-[#666555] leading-relaxed">{attack.findings}</p>
                        </div>
                        <div className="p-3 rounded-lg bg-[#FBF8F4] border border-[#E8DDD2]">
                          <span className="font-bold text-[#2ECC71] block mb-1">Remediation Installed:</span>
                          <p className="text-[#666555] leading-relaxed">{attack.recommendation}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: COST LEDGER */}
      {activeTab === 'cost' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-[#F0E6DC]/50 border border-[#E8DDD2] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <span className="text-xs font-bold text-[#3D3229]">Total Red-Team Evaluation Cost</span>
              <div className="text-2xl font-black text-[#C75A3B] font-mono mt-0.5">
                ${scenario.costSummary.total.toFixed(2)}
              </div>
            </div>
            <div className="text-xs text-[#666555] sm:text-right">
              <div>Budget Capped at <span className="font-mono font-bold text-[#3D3229]">$5.00</span></div>
              <div className="text-[#2ECC71] font-semibold">1000x cheaper than manual pentesting ($50k+)</div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Cost by Stage */}
            <div className="p-4 rounded-xl bg-[#FBF8F4] border border-[#E8DDD2] space-y-3">
              <span className="text-xs font-bold text-[#3D3229] uppercase tracking-wider block">
                Cost Breakdown by Pipeline Stage
              </span>
              {Object.entries(scenario.costSummary.byStage).map(([stage, cost]) => (
                <div key={stage} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#666555]">{stage}</span>
                    <span className="font-mono font-bold text-[#3D3229]">${(cost as number).toFixed(2)}</span>
                  </div>
                  <div className="w-full h-1 bg-[#E8DDD2] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#C75A3B]"
                      style={{ width: `${((cost as number) / scenario.costSummary.total) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Cost by Model */}
            <div className="p-4 rounded-xl bg-[#FBF8F4] border border-[#E8DDD2] space-y-3">
              <span className="text-xs font-bold text-[#3D3229] uppercase tracking-wider block">
                Multi-Model Cost Distribution
              </span>
              {Object.entries(scenario.costSummary.byModel).map(([model, cost]) => (
                <div key={model} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#666555]">{model}</span>
                    <span className="font-mono font-bold text-[#3D3229]">${(cost as number).toFixed(2)}</span>
                  </div>
                  <div className="w-full h-1 bg-[#E8DDD2] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#2ECC71]"
                      style={{ width: `${((cost as number) / scenario.costSummary.total) * 100}%` }}
                    />
                  </div>
                </div>
              ))}

              <div className="pt-2 border-t border-[#E8DDD2] flex items-center justify-between text-[11px] font-mono text-[#666555]">
                <span>Total Tokens: {scenario.costSummary.tokensTotal.toLocaleString()}</span>
                <span>Cache Hit: {scenario.costSummary.cacheHitRate}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: HARDENING & CERTIFICATE */}
      {activeTab === 'diff' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-[#2ECC71]/10 border border-[#2ECC71]/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Award className="w-8 h-8 text-[#2ECC71] shrink-0" />
              <div>
                <span className="text-xs font-mono uppercase font-bold text-[#2ECC71]">
                  PROMPTFORGE VERIFIED CERTIFICATE
                </span>
                <h3 className="text-sm sm:text-base font-bold text-[#3D3229]">
                  Cryptographic Production Birth Certificate
                </h3>
              </div>
            </div>

            <button
              onClick={copyCertHash}
              className="px-3 py-1.5 bg-[#FBF8F4] border border-[#E8DDD2] hover:border-[#2ECC71] text-xs font-mono font-semibold text-[#3D3229] rounded-lg transition flex items-center gap-1.5"
            >
              {copiedHash ? <Check className="w-3.5 h-3.5 text-[#2ECC71]" /> : <Copy className="w-3.5 h-3.5 text-[#666555]" />}
              <span>{copiedHash ? 'Hash Copied!' : 'Copy SHA-256'}</span>
            </button>
          </div>

          <div className="p-3 rounded-lg bg-[#F0E6DC]/40 border border-[#E8DDD2] text-[11px] font-mono text-[#666555] break-all">
            <span className="font-bold text-[#3D3229]">Certificate SHA-256: </span>
            {scenario.hardeningSummary.birthCertificateSha256}
          </div>

          <div className="p-4 rounded-xl bg-[#FBF8F4] border border-[#E8DDD2] space-y-2">
            <span className="text-xs font-bold text-[#3D3229] uppercase tracking-wider block">
              Automated Hardening Patches Injected
            </span>
            <div className="space-y-1.5">
              {scenario.hardeningSummary.diffHighlights.map((patch, i) => (
                <div
                  key={i}
                  className="p-2 rounded bg-[#2ECC71]/5 border border-[#2ECC71]/20 font-mono text-xs text-[#27AE60]"
                >
                  {patch}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
