'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  Award,
  FileCheck,
  RotateCcw,
  Send,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import MainNav from '../../components/MainNav';
import AuditModeEntry from '../../components/AuditModeEntry';
import VerificationScorecardView, { VerificationScorecardData } from '../../components/VerificationScorecardView';
import HardeningLogView, { HardeningLogData } from '../../components/HardeningLogView';
import AgentChatWindow, { BlueprintInfo } from '../../components/AgentChatWindow';
import { API_BASE_URL } from '../../lib/api';

export default function AuditPage() {
  const [tenantId, setTenantId] = useState('tenant-demo');
  const [auditResult, setAuditResult] = useState<{
    blueprint: BlueprintInfo;
    scorecard: VerificationScorecardData;
    hardeningLog: HardeningLogData | null;
    birthCertificateId: string;
  } | null>(null);

  const [activeTab, setActiveTab] = useState<'scorecard' | 'hardening' | 'chat'>('scorecard');

  const handleAuditComplete = (result: {
    blueprint: BlueprintInfo;
    scorecard: VerificationScorecardData;
    hardeningLog: HardeningLogData | null;
    birthCertificateId: string;
  }) => {
    setAuditResult(result);
    setActiveTab('scorecard');
  };

  const handleReset = () => {
    setAuditResult(null);
  };

  return (
    <main className="min-h-screen bg-[#F9F5F0] text-[#3D3229] font-sans selection:bg-[#C75A3B] selection:text-white pb-20">
      {/* Platform Global Top Navigation */}
      <MainNav
        activeStage="audit"
        activeTenant={tenantId}
        onTenantChange={setTenantId}
      />

      <div className="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        {!auditResult ? (
          <AuditModeEntry
            apiBaseUrl={API_BASE_URL}
            tenantId={tenantId}
            onAuditComplete={handleAuditComplete}
            onError={(err) => console.error('Audit Error:', err)}
          />
        ) : (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Audit Completion Banner */}
            <div className="w-full bg-[#FBF8F4] border border-[#2ECC71]/40 rounded-2xl p-6 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-[#2ECC71]/15 text-[#2ECC71] border border-[#2ECC71]/30 flex items-center justify-center shrink-0">
                  <Award className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#2ECC71]/15 text-[#2ECC71] border border-[#2ECC71]/30">
                      Audit Complete &amp; Certified
                    </span>
                    <span className="text-xs text-[#666555] font-mono">
                      Cert ID: {auditResult.birthCertificateId}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-[#3D3229] mt-1">
                    {auditResult.blueprint.agent_name}
                  </h2>
                  <p className="text-xs text-[#666555] mt-0.5">
                    Agent passed zero-trust adversarial red teaming, self-hardening patch enforcement, and ground-truth verification.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 flex-wrap">
                <Link
                  href={`/dossier?agentId=${auditResult.blueprint.blueprint_id}`}
                  className="btn-primary text-xs flex items-center gap-1.5"
                >
                  <FileCheck className="w-4 h-4" />
                  <span>View Passport Dossier</span>
                  <ExternalLink className="w-3.5 h-3.5 opacity-70" />
                </Link>
                <button
                  type="button"
                  onClick={handleReset}
                  className="btn-secondary text-xs flex items-center gap-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Audit Another Agent</span>
                </button>
              </div>
            </div>

            {/* View Tabs */}
            <div className="flex items-center gap-2 border-b border-[#E8DDD2] pb-3">
              <button
                type="button"
                onClick={() => setActiveTab('scorecard')}
                className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  activeTab === 'scorecard'
                    ? 'bg-[#C75A3B] text-white shadow-sm'
                    : 'bg-white border border-[#E8DDD2] text-[#666555] hover:text-[#3D3229]'
                }`}
              >
                <Award className="w-4 h-4" />
                <span>Verification Scorecard</span>
              </button>

              {auditResult.hardeningLog && (
                <button
                  type="button"
                  onClick={() => setActiveTab('hardening')}
                  className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                    activeTab === 'hardening'
                      ? 'bg-[#C75A3B] text-white shadow-sm'
                      : 'bg-white border border-[#E8DDD2] text-[#666555] hover:text-[#3D3229]'
                  }`}
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Self-Hardening Patches</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => setActiveTab('chat')}
                className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  activeTab === 'chat'
                    ? 'bg-[#C75A3B] text-white shadow-sm'
                    : 'bg-white border border-[#E8DDD2] text-[#666555] hover:text-[#3D3229]'
                }`}
              >
                <Send className="w-4 h-4" />
                <span>Live Test Sandbox</span>
              </button>
            </div>

            {/* Tab Views */}
            {activeTab === 'scorecard' && (
              <div className="animate-in fade-in duration-200">
                <VerificationScorecardView
                  scorecard={auditResult.scorecard}
                  agentName={auditResult.blueprint.agent_name}
                  onBackToChat={() => setActiveTab('chat')}
                />
              </div>
            )}

            {activeTab === 'hardening' && auditResult.hardeningLog && (
              <div className="animate-in fade-in duration-200">
                <HardeningLogView
                  hardeningLog={auditResult.hardeningLog}
                  agentName={auditResult.blueprint.agent_name}
                  onProceedToVerification={() => setActiveTab('scorecard')}
                  onChatWithHardenedAgent={() => setActiveTab('chat')}
                />
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="animate-in fade-in duration-200">
                <AgentChatWindow
                  blueprint={auditResult.blueprint}
                  onReset={handleReset}
                  apiBaseUrl={API_BASE_URL}
                  tenantId={tenantId}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
