'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { Flame, ArrowLeft, ArrowRight, ShieldCheck, Sparkles, RefreshCw } from 'lucide-react';
import MainNav from '../../components/MainNav';
import { API_BASE_URL, apiFetch } from '../../lib/api';

const RedTeamFeed = dynamic(() => import('../../components/RedTeamFeed'), { ssr: false });

const DEFAULT_DEMO_AGENT = {
  blueprint_id: 'demo-blueprint-1',
  agent_name: 'Customer Support Assistant'
};

export default function RedTeamPage() {
  const [tenantId, setTenantId] = useState('tenant-demo');
  const [activeBlueprint, setActiveBlueprint] = useState<{
    blueprint_id: string;
    agent_name: string;
  }>(DEFAULT_DEMO_AGENT);
  const [recentBlueprints, setRecentBlueprints] = useState<Array<{ blueprint_id: string; agent_name: string }>>([]);

  useEffect(() => {
    // Attempt to load most recently forged agent from localStorage or API
    try {
      const saved = localStorage.getItem('promptforge_last_session');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.blueprint && parsed.blueprint.blueprint_id) {
          setActiveBlueprint({
            blueprint_id: parsed.blueprint.blueprint_id,
            agent_name: parsed.blueprint.agent_name || 'Active Agent'
          });
        }
      }
    } catch (e) {
      // Ignore fallback
    }

    // Also fetch available agents for this tenant
    const fetchAgents = async () => {
      try {
        const res = await apiFetch(`${API_BASE_URL}/api/deploy/agents`, {}, tenantId);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setRecentBlueprints(data.map((a: any) => ({
              blueprint_id: a.agent_id || a.blueprint_id,
              agent_name: a.agent_name || a.name || 'Agent'
            })));
          }
        }
      } catch {
        // Fallback to demo
      }
    };
    fetchAgents();
  }, [tenantId]);

  return (
    <main className="min-h-screen bg-[#F9F5F0] text-[#3D3229] font-sans selection:bg-[#C75A3B] selection:text-white pb-20">
      <MainNav
        activeStage="redteam"
        activeTenant={tenantId}
        onTenantChange={setTenantId}
      />

      <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-6">
        {/* Agent Selector Toolbar */}
        <div className="w-full bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-4 shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#E74C3C]/15 text-[#E74C3C] flex items-center justify-center font-bold">
              <Flame className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-[#3D3229]">Red Team Attack Studio</h1>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#E74C3C]/15 text-[#E74C3C] font-semibold border border-[#E74C3C]/30">
                  STAGE 4
                </span>
              </div>
              <p className="text-xs text-[#666555] mt-0.5">
                Target: <span className="font-semibold text-[#3D3229]">{activeBlueprint.agent_name}</span>{' '}
                <code className="text-[10px] text-[#9B8B7E] font-mono">({activeBlueprint.blueprint_id})</code>
              </p>
            </div>
          </div>

          {recentBlueprints.length > 1 && (
            <div className="flex items-center gap-2">
              <label className="text-xs text-[#666555] font-medium">Switch Target:</label>
              <select
                value={activeBlueprint.blueprint_id}
                onChange={(e) => {
                  const found = recentBlueprints.find(b => b.blueprint_id === e.target.value);
                  if (found) setActiveBlueprint(found);
                }}
                className="text-xs bg-white border border-[#E8DDD2] rounded-lg px-2.5 py-1.5 text-[#3D3229] focus:outline-none focus:border-[#C75A3B]"
              >
                {recentBlueprints.map(bp => (
                  <option key={bp.blueprint_id} value={bp.blueprint_id}>
                    {bp.agent_name} ({bp.blueprint_id.slice(0, 8)})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Live Attack Feed */}
        <div className="animate-in fade-in duration-300">
          <RedTeamFeed
            blueprintId={activeBlueprint.blueprint_id}
            agentName={activeBlueprint.agent_name}
            tenantId={tenantId}
            onBackToChat={() => window.location.href = '/'}
            onProceedToHardening={() => window.location.href = '/evolve'}
          />
        </div>
      </div>
    </main>
  );
}
