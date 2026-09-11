'use client';

import React, { useState, useEffect } from 'react';
import { Bot, Swords, Target, Scale, ShieldAlert, ShieldCheck, AlertTriangle, Activity, DollarSign } from 'lucide-react';

export interface AttackCascadeStep {
  id: number;
  label: string;
  icon: React.ReactNode;
  duration: number;
  description: string;
}

export interface AttackCascadeProps {
  active?: boolean;
  targetModel?: string;
  personaName?: string;
  attackVariant?: string;
  severity?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  verdict?: 'BLOCKED' | 'DEGRADED' | 'COMPROMISED';
  judgeModel?: string;
  confidenceScore?: number;
  costUsd?: number;
  tokensIn?: number;
  tokensOut?: number;
  onComplete?: () => void;
}

export default function AttackCascade({
  active = true,
  targetModel = 'openai/gpt-oss-120b',
  personaName = 'Jailbreak Specialist',
  attackVariant = 'Adversarial Suffix Injection v3',
  severity = 'CRITICAL',
  verdict = 'BLOCKED',
  judgeModel = 'openai/gpt-oss-120b (Judge)',
  confidenceScore = 98,
  costUsd = 0.0284,
  tokensIn = 840,
  tokensOut = 195,
  onComplete,
}: AttackCascadeProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [tickerCost, setTickerCost] = useState(0.002);

  const steps: AttackCascadeStep[] = [
    {
      id: 1,
      label: 'Persona Generation',
      icon: <Bot className="w-4 h-4 text-[#C75A3B]" />,
      duration: 1000,
      description: `Synthesizing attack persona: "${personaName}"`,
    },
    {
      id: 2,
      label: 'Adversarial Crafting',
      icon: <Swords className="w-4 h-4 text-[#D97D5E]" />,
      duration: 1400,
      description: `Formulating attack vectors: "${attackVariant}"`,
    },
    {
      id: 3,
      label: 'Target Model Execution',
      icon: <Target className="w-4 h-4 text-[#F39C12]" />,
      duration: 2000,
      description: `Executing against ${targetModel}...`,
    },
    {
      id: 4,
      label: 'Non-Circular Judge Scoring',
      icon: <Scale className="w-4 h-4 text-[#2ECC71]" />,
      duration: 1200,
      description: `Cross-evaluating safety policy with ${judgeModel}`,
    },
  ];

  // Animated progression
  useEffect(() => {
    if (!active) {
      setCurrentStep(steps.length + 1);
      return;
    }

    setCurrentStep(1);
    let accumulated = 0;
    const timers: NodeJS.Timeout[] = [];

    const tickerInterval = setInterval(() => {
      setTickerCost((prev) => +(prev + 0.0035).toFixed(4));
    }, 400);

    steps.forEach((step, idx) => {
      accumulated += step.duration;
      const t = setTimeout(() => {
        setCurrentStep(idx + 2);
        if (idx === steps.length - 1) {
          clearInterval(tickerInterval);
          setTickerCost(costUsd);
          onComplete?.();
        }
      }, accumulated);
      timers.push(t);
    });

    return () => {
      timers.forEach(clearTimeout);
      clearInterval(tickerInterval);
    };
  }, [active, personaName, attackVariant]);

  const severityBadge = {
    CRITICAL: 'bg-[#E74C3C]/15 text-[#E74C3C] border-[#E74C3C]/30 font-bold',
    HIGH: 'bg-[#F39C12]/15 text-[#F39C12] border-[#F39C12]/30 font-bold',
    MEDIUM: 'bg-[#C75A3B]/15 text-[#C75A3B] border-[#C75A3B]/30 font-bold',
    LOW: 'bg-[#F0E6DC] text-[#666555] border-[#E8DDD2]',
  }[severity];

  const verdictBadge = {
    BLOCKED: 'bg-[#2ECC71]/15 text-[#2ECC71] border-[#2ECC71]/30 font-bold',
    DEGRADED: 'bg-[#F39C12]/15 text-[#F39C12] border-[#F39C12]/30 font-bold',
    COMPROMISED: 'bg-[#E74C3C]/15 text-[#E74C3C] border-[#E74C3C]/30 font-bold',
  }[verdict];

  return (
    <div className="w-full bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-5 md:p-6 shadow-card space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E8DDD2] pb-3.5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[#F0E6DC] text-[#C75A3B] border border-[#E8DDD2]">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-[#3D3229] tracking-tight">Live Adversarial Attack Cascade</h4>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-[#C75A3B]/10 text-[#C75A3B] border border-[#C75A3B]/25 font-bold">
                Automated
              </span>
            </div>
            <p className="text-[11px] text-[#666555]">Step-by-step adversary simulation with live cost telemetry</p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-[#3D3229] bg-[#F0E6DC] px-3 py-1.5 rounded-lg border border-[#E8DDD2]">
          <DollarSign className="w-3.5 h-3.5 text-[#C75A3B]" />
          <span>Live Run Cost:</span>
          <span className="font-bold text-[#C75A3B]">${tickerCost.toFixed(4)}</span>
        </div>
      </div>

      {/* Attack Pipeline Steps */}
      <div className="space-y-3">
        {steps.map((step, idx) => {
          const stepNum = idx + 1;
          const isDone = currentStep > stepNum;
          const isCurrent = currentStep === stepNum;

          return (
            <div
              key={step.id}
              className={`p-3.5 rounded-xl border transition-all duration-300 ${
                isCurrent
                  ? 'bg-white border-[#C75A3B] shadow-card-hover'
                  : isDone
                  ? 'bg-white border-[#2ECC71]/30 opacity-95'
                  : 'bg-[#F0E6DC]/40 border-[#E8DDD2] opacity-50'
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-mono font-bold ${
                      isDone
                        ? 'bg-[#2ECC71]/15 text-[#2ECC71] border border-[#2ECC71]/40'
                        : isCurrent
                        ? 'bg-[#C75A3B]/15 text-[#C75A3B] border border-[#C75A3B]/40'
                        : 'bg-[#E8DDD2] text-[#9B8B7E]'
                    }`}
                  >
                    {isDone ? '✓' : step.icon}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-semibold ${isCurrent ? 'text-[#3D3229]' : 'text-[#666555]'}`}>
                        Step {stepNum}: {step.label}
                      </span>
                      {isCurrent && (
                        <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#C75A3B]/15 text-[#C75A3B] font-bold animate-pulse">
                          Processing
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#666555] font-mono mt-0.5">{step.description}</p>
                  </div>
                </div>

                <span className="text-[10px] font-mono font-semibold text-[#9B8B7E]">
                  {isDone ? 'PASS' : isCurrent ? 'RUNNING' : 'QUEUED'}
                </span>
              </div>

              {/* Progress bar shimmer for current step */}
              {isCurrent && (
                <div className="w-full h-1.5 bg-[#E8DDD2] rounded-full overflow-hidden mt-3">
                  <div className="h-full progress-bar-shimmer rounded-full" style={{ width: '85%' }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Results Banner (Appears when completed) */}
      {currentStep > steps.length && (
        <div className="p-4 rounded-xl bg-white border border-[#2ECC71]/40 space-y-3 shadow-xs animate-in fade-in duration-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold uppercase px-2.5 py-1 rounded-lg border ${verdictBadge}`}>
                Verdict: {verdict}
              </span>
              <span className={`text-[11px] font-mono uppercase px-2 py-0.5 rounded border ${severityBadge}`}>
                Severity: {severity}
              </span>
              <span className="text-xs text-[#3D3229] font-medium">
                Judge Confidence: <strong className="text-[#2ECC71]">{confidenceScore}%</strong>
              </span>
            </div>

            <div className="flex items-center gap-3 font-mono text-[11px] text-[#666555]">
              <span>Tokens: <strong className="text-[#3D3229]">{tokensIn}</strong> in, <strong className="text-[#3D3229]">{tokensOut}</strong> out</span>
              <span className="text-[#E8DDD2]">·</span>
              <span>Final Cost: <strong className="text-[#C75A3B]">${costUsd.toFixed(4)}</strong></span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
