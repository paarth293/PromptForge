'use client';

import React, { useEffect, useState } from 'react';
import { ShieldCheck, Cpu, Activity, AlertCircle, CheckCircle2 } from 'lucide-react';

interface HealthData {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        setLoading(true);
        const res = await fetch('http://localhost:8000/health');
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        const data: HealthData = await res.json();
        setHealth(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to reach backend');
      } finally {
        setLoading(false);
      }
    };

    checkBackend();
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-[#0B0F17] text-slate-100">
      <div className="max-w-2xl w-full bg-[#121826] border border-[#232D42] rounded-2xl p-8 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30">
            <Cpu className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              PromptForge
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 font-medium">
                Phase 0 Scaffold
              </span>
            </h1>
            <p className="text-sm text-slate-400">
              The Self-Hardening Forge for AI Agents — Built Entirely Through Prompts
            </p>
          </div>
        </div>

        <div className="my-6 border-t border-[#232D42]" />

        <div className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            System Connectivity Status
          </h2>

          <div className="p-4 rounded-xl bg-[#0F1420] border border-[#232D42] flex items-center justify-between">
            <div className="flex items-center gap-3">
              {loading ? (
                <div className="w-3 h-3 rounded-full bg-yellow-400 animate-pulse" />
              ) : health?.status === 'healthy' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-rose-400" />
              )}
              <div>
                <div className="text-sm font-medium text-white">Backend Health API</div>
                <div className="text-xs text-slate-400">
                  {loading
                    ? 'Connecting to http://localhost:8000/health...'
                    : error
                    ? `Status: Error (${error})`
                    : `backend: ${health?.status} (service: ${health?.service}, v${health?.version})`}
                </div>
              </div>
            </div>

            <div className="text-right">
              {health?.status === 'healthy' && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  ONLINE
                </span>
              )}
              {error && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  OFFLINE
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-[#232D42] flex items-center justify-between text-xs text-slate-500">
          <span>PromptForge Engine v0.1.0</span>
          <span>14 Chains • Deterministic Spine</span>
        </div>
      </div>
    </main>
  );
}
