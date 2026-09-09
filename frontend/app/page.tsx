'use client';

import React, { useState } from 'react';
import {
  Wrench,
  Shield,
  Send,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Terminal,
  Cpu,
  RefreshCw,
  Flame
} from 'lucide-react';
import SpecConfirmationCard, { AgentSpecData } from '../components/SpecConfirmationCard';
import AgentChatWindow, { BlueprintInfo } from '../components/AgentChatWindow';
import RedTeamFeed from '../components/RedTeamFeed';
import HardeningLogView, { HardeningLogData } from '../components/HardeningLogView';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type ForgeStage = 'input' | 'confirm_spec' | 'assembling' | 'chat' | 'redteam' | 'harden';

export default function HomePage() {
  const [stage, setStage] = useState<ForgeStage>('input');
  const [promptInput, setPromptInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stored state across stages
  const [spec, setSpec] = useState<AgentSpecData | null>(null);
  const [blueprint, setBlueprint] = useState<BlueprintInfo | null>(null);
  const [hardeningLog, setHardeningLog] = useState<HardeningLogData | null>(null);
  const [assemblySteps, setAssemblySteps] = useState<
    { name: string; chain: string; status: 'pending' | 'running' | 'done' }[]
  >([
    { name: 'Intent Decomposition', chain: 'Chain 1', status: 'done' },
    { name: 'Ground-Truth Test Set & Edge Cases', chain: 'Chain 14', status: 'pending' },
    { name: 'CRISPE System Prompt Synthesis', chain: 'Chain 2', status: 'pending' },
    { name: 'OpenAI-Compatible Tool Schema Generation', chain: 'Chain 3', status: 'pending' },
    { name: 'Two-Layer Guardrail Construction & Probe Validation', chain: 'Chain 4', status: 'pending' },
    { name: 'Canonical Few-Shot Exemplar Dialogues', chain: 'Chain 5', status: 'pending' },
    { name: 'SHA-256 Tamper-Evident Hash Chain Assembly', chain: 'Spine', status: 'pending' }
  ]);

  // Quick preset templates
  const presets = [
    {
      title: 'Customer Support Bot',
      description: 'Retail customer support agent that handles order inquiries, refunds up to $500, and escalates complex issues.'
    },
    {
      title: 'Sales Lead Qualifier',
      description: 'Inbound sales qualification agent that scores enterprise leads, books demos, and collects company budget.'
    },
    {
      title: 'Internal IT Helpdesk',
      description: 'Internal IT support agent that troubleshoots SSO, resets tokens within authorized scopes, and files bug tickets.'
    }
  ];

  // 1. Decompose intent
  const handleDecompose = async (textToDecompose?: string) => {
    const text = (textToDecompose || promptInput).trim();
    if (!text) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/forge/decompose`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': 'tenant-demo'
        },
        body: JSON.stringify({ description: text })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${res.status}`);
      }

      const specData: AgentSpecData = await res.json();
      setSpec(specData);
      setStage('confirm_spec');
    } catch (err: any) {
      setError(err.message || 'Failed to decompose intent');
    } finally {
      setLoading(false);
    }
  };

  // 2. Confirm spec and trigger assembly
  const handleConfirmSpec = async (updatedSpec: AgentSpecData) => {
    setLoading(true);
    setError(null);

    try {
      // Step A: Save spec corrections
      const confirmRes = await fetch(`${API_BASE_URL}/api/forge/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': 'tenant-demo'
        },
        body: JSON.stringify(updatedSpec)
      });

      if (!confirmRes.ok) {
        throw new Error(`Failed to confirm spec (status ${confirmRes.status})`);
      }

      const confirmedData = await confirmRes.json();
      setSpec(confirmedData);
      setStage('assembling');

      // Animate compilation steps visually while server assembles
      simulateAssemblyProgress(confirmedData.spec_id);
    } catch (err: any) {
      setError(err.message || 'Error confirming spec');
      setLoading(false);
    }
  };

  // 3. Trigger assembly and visual progress
  const simulateAssemblyProgress = async (specId: string) => {
    // Progress animation
    const updateStep = (index: number, status: 'running' | 'done') => {
      setAssemblySteps((prev) =>
        prev.map((s, i) => (i === index ? { ...s, status } : s))
      );
    };

    updateStep(1, 'running');
    setTimeout(() => updateStep(1, 'done'), 400);

    updateStep(2, 'running');
    setTimeout(() => updateStep(2, 'done'), 800);

    updateStep(3, 'running');
    setTimeout(() => updateStep(3, 'done'), 1200);

    updateStep(4, 'running');
    setTimeout(() => updateStep(4, 'done'), 1600);

    updateStep(5, 'running');
    setTimeout(() => updateStep(5, 'done'), 2000);

    try {
      const res = await fetch(`${API_BASE_URL}/api/forge/assemble/${specId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': 'tenant-demo'
        }
      });

      if (!res.ok) {
        throw new Error(`Assembly failed with HTTP ${res.status}`);
      }

      const bp = await res.json();
      updateStep(6, 'done');

      setTimeout(() => {
        setBlueprint({
          blueprint_id: bp.blueprint_id,
          agent_name: bp.agent_name,
          system_prompt: bp.system_prompt,
          blueprint_hash: bp.blueprint_hash,
          tools: bp.tools || [],
          guardrails: bp.guardrails || []
        });
        setStage('chat');
        setLoading(false);
      }, 500);
    } catch (err: any) {
      setError(err.message || 'Failed to assemble agent blueprint');
      setLoading(false);
    }
  };

  const handleReset = () => {
    setStage('input');
    setPromptInput('');
    setSpec(null);
    setBlueprint(null);
    setError(null);
  };

  return (
    <main className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col items-center justify-start p-4 md:p-8">
      {/* Top Navbar */}
      <header className="w-full max-w-5xl flex items-center justify-between py-4 border-b border-[#232D42] mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30 flex items-center justify-center">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">PromptForge</h1>
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Self-Hardening AI Forge
              </span>
            </div>
            <p className="text-xs text-slate-400">The product IS prompt engineering • 14 Chains + Deterministic Spine</p>
          </div>
        </div>

        {/* Stage Breadcrumb */}
        <div className="hidden sm:flex items-center gap-2 text-xs font-medium text-slate-400">
          <span className={`px-2.5 py-1 rounded-lg ${stage === 'input' ? 'bg-blue-600 text-white' : 'bg-[#151C2C]'}`}>
            1. Describe
          </span>
          <span>→</span>
          <span className={`px-2.5 py-1 rounded-lg ${stage === 'confirm_spec' ? 'bg-blue-600 text-white' : 'bg-[#151C2C]'}`}>
            2. Confirm Spec
          </span>
          <span>→</span>
          <span className={`px-2.5 py-1 rounded-lg ${stage === 'assembling' ? 'bg-blue-600 text-white' : 'bg-[#151C2C]'}`}>
            3. Forge
          </span>
          <span>→</span>
          <span className={`px-2.5 py-1 rounded-lg ${stage === 'chat' ? 'bg-blue-600 text-white' : 'bg-[#151C2C]'}`}>
            4. Live Chat
          </span>
          <span>→</span>
          <span className={`px-2.5 py-1 rounded-lg ${stage === 'redteam' ? 'bg-red-600 text-white' : 'bg-[#151C2C]'}`}>
            5. Red Team
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="w-full max-w-5xl flex-1 flex flex-col items-center">
        {error && (
          <div className="w-full mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)} className="text-slate-400 hover:text-white">&times;</button>
          </div>
        )}

        {/* STAGE 1: Natural Language Prompt Input */}
        {stage === 'input' && (
          <div className="w-full space-y-8 animate-in fade-in duration-300">
            <div className="text-center space-y-3 max-w-2xl mx-auto pt-6">
              <h2 className="text-3xl font-extrabold text-white tracking-tight">
                One sentence in, an attack-hardened agent out.
              </h2>
              <p className="text-sm text-slate-400">
                Type what your agent should do. PromptForge will infer unstated security policies,
                synthesize CRISPE system prompts, build function tools, and attach verified guardrails.
              </p>
            </div>

            {/* Input Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleDecompose();
              }}
              className="bg-[#121826] border border-[#232D42] rounded-2xl p-6 shadow-2xl space-y-4"
            >
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                Agent Intent Description
              </label>
              <div className="relative">
                <textarea
                  rows={3}
                  value={promptInput}
                  onChange={(e) => setPromptInput(e.target.value)}
                  placeholder="e.g. Build me a customer support agent that checks order status and issues refunds under $500."
                  className="w-full p-4 bg-[#0B0F17] border border-[#232D42] rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-slate-500">
                  Runs Chain 1 (Intent Decomposition) + Risk Domain Detection
                </span>
                <button
                  type="submit"
                  disabled={loading || !promptInput.trim()}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-500/20 disabled:opacity-50 transition-all"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Decomposing Intent...
                    </>
                  ) : (
                    <>
                      Decompose & Confirm Spec
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Presets */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Or try a sample demo agent:
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {presets.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setPromptInput(preset.description);
                      handleDecompose(preset.description);
                    }}
                    className="p-4 rounded-xl bg-[#121826] border border-[#232D42] hover:border-blue-500/50 text-left transition-all hover:shadow-lg hover:shadow-blue-500/5 group"
                  >
                    <div className="text-sm font-semibold text-white group-hover:text-blue-400 flex items-center justify-between">
                      {preset.title}
                      <Sparkles className="w-3.5 h-3.5 opacity-60" />
                    </div>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                      {preset.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* STAGE 2: Spec Confirmation Card */}
        {stage === 'confirm_spec' && spec && (
          <div className="w-full space-y-4 animate-in fade-in duration-300">
            <SpecConfirmationCard
              spec={spec}
              onConfirm={handleConfirmSpec}
              loading={loading}
            />
          </div>
        )}

        {/* STAGE 3: Assembling Animation */}
        {stage === 'assembling' && (
          <div className="w-full max-w-xl bg-[#121826] border border-[#232D42] rounded-2xl p-8 shadow-2xl space-y-6 my-auto animate-in zoom-in-95 duration-300">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mx-auto">
                <RefreshCw className="w-6 h-6 animate-spin text-blue-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Forging Autonomous Agent Blueprint</h2>
              <p className="text-xs text-slate-400">
                Executing Prompt Chains 2–5 and establishing cryptographic SHA-256 fingerprint
              </p>
            </div>

            <div className="space-y-3 pt-2">
              {assemblySteps.map((step, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-xl bg-[#0F1420] border border-[#232D42] text-xs"
                >
                  <div className="flex items-center gap-3">
                    {step.status === 'done' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : step.status === 'running' ? (
                      <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-700" />
                    )}
                    <span className={step.status === 'done' ? 'text-white font-medium' : 'text-slate-400'}>
                      {step.name}
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-500 uppercase px-2 py-0.5 rounded bg-black/40 border border-slate-800">
                    {step.chain}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STAGE 4: Interactive Live Agent Chat */}
        {stage === 'chat' && blueprint && (
          <div className="w-full animate-in fade-in duration-300">
            <AgentChatWindow
              blueprint={blueprint}
              onReset={handleReset}
              onLaunchRedTeam={() => setStage('redteam')}
              apiBaseUrl={API_BASE_URL}
            />
          </div>
        )}

        {/* STAGE 5: Live Streaming Red Team Feed */}
        {stage === 'redteam' && blueprint && (
          <div className="w-full animate-in fade-in duration-300">
            <RedTeamFeed
              blueprintId={blueprint.blueprint_id}
              agentName={blueprint.agent_name}
              onBackToChat={() => setStage('chat')}
              onProceedToHardening={async () => {
                setLoading(true);
                setError(null);
                try {
                  const res = await fetch(`${API_BASE_URL}/api/harden/run/${blueprint.blueprint_id}`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'X-Tenant-ID': 'tenant-demo'
                    }
                  });
                  if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || 'Hardening loop failed');
                  }
                  const loopResult = await res.json();
                  setHardeningLog(loopResult.hardening_log);
                  setStage('harden');
                } catch (err: any) {
                  setError(err.message || 'Hardening failed');
                } finally {
                  setLoading(false);
                }
              }}
            />
          </div>
        )}

        {/* STAGE 6: Automated Guardrail Hardening Log View */}
        {stage === 'harden' && blueprint && hardeningLog && (
          <div className="w-full animate-in fade-in duration-300">
            <HardeningLogView
              hardeningLog={hardeningLog}
              agentName={blueprint.agent_name}
              onBackToRedTeam={() => setStage('redteam')}
              onChatWithHardenedAgent={() => setStage('chat')}
            />
          </div>
        )}
      </div>
    </main>
  );
}
