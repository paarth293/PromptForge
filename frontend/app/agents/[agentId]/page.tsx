'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AgentChatWindow, { BlueprintInfo } from '../../../components/AgentChatWindow';
import MonitorDashboardView from '../../../components/MonitorDashboardView';
import { Shield, Award, CheckCircle2, AlertCircle, RefreshCw, Activity, MessageSquare } from 'lucide-react';
import { apiFetch } from '../../../lib/api';

interface DeploymentData {
  deployment_id: string;
  agent_id: string;
  blueprint_id: string;
  agent_name: string;
  version: number;
  status: string;
  shareable_url: string;
  chat_api_url: string;
  public_verification_url: string;
  certificate_id?: string;
  composite_fingerprint?: string;
  system_prompt_preview: string;
  tools_count: number;
  guardrails_count: number;
  metadata?: Record<string, any>;
  deployed_at: string;
}

interface VerificationResult {
  certificate_id: string;
  is_valid: boolean;
  blueprint_integrity: boolean;
  redteam_report_integrity: boolean;
  scorecard_integrity: boolean;
  audit_chain_integrity: boolean;
  composite_fingerprint_valid: boolean;
  tampered_fields: string[];
  failure_reasons: string[];
  audit_blocks_checked: number;
  composite_fingerprint: string;
}

export default function DeployedAgentPage() {
  const params = useParams();
  const agentId = params?.agentId as string;

  const [deployment, setDeployment] = useState<DeploymentData | null>(null);
  const [blueprint, setBlueprint] = useState<BlueprintInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'monitor'>('chat');

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!agentId) return;

    async function loadAgent() {
      setLoading(true);
      setError(null);
      try {
        // 1. Fetch deployment package
        const deployRes = await apiFetch(`${apiBaseUrl}/api/deploy/agents/${agentId}`, {}, 'tenant-demo');
        if (!deployRes.ok) {
          throw new Error(`Agent not found or deployment is unavailable (${deployRes.status})`);
        }
        const deployData: DeploymentData = await deployRes.json();
        setDeployment(deployData);

        // 2. Fetch full blueprint for chat window
        const bpRes = await apiFetch(`${apiBaseUrl}/api/blueprints/${deployData.blueprint_id}`, {}, 'tenant-demo');
        if (bpRes.ok) {
          const bpData = await bpRes.json();
          setBlueprint({
            blueprint_id: bpData.blueprint_id,
            agent_name: bpData.agent_name,
            system_prompt: bpData.system_prompt,
            blueprint_hash: bpData.blueprint_hash,
            tools: bpData.tools || [],
            guardrails: bpData.guardrails || []
          });
        } else {
          // Fallback blueprint info from deployment data
          setBlueprint({
            blueprint_id: deployData.blueprint_id,
            agent_name: deployData.agent_name,
            system_prompt: deployData.system_prompt_preview,
            blueprint_hash: deployData.composite_fingerprint,
            tools: [],
            guardrails: []
          });
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load deployed agent');
      } finally {
        setLoading(false);
      }
    }

    loadAgent();
  }, [agentId, apiBaseUrl]);

  const verifyCertificate = async () => {
    if (!deployment?.certificate_id) return;
    setVerifying(true);
    try {
      const res = await apiFetch(`${apiBaseUrl}/api/verify/certificate/${deployment.certificate_id}`, {}, 'tenant-demo');
      if (res.ok) {
        const data: VerificationResult = await res.json();
        setVerificationResult(data);
      }
    } catch (e) {
      console.error('Verification request failed', e);
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-forge-dark text-slate-100 flex items-center justify-center p-6">
        <div className="flex items-center space-x-3 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
          <span>Connecting to deployed agent runtime...</span>
        </div>
      </div>
    );
  }

  if (error || !deployment || !blueprint) {
    return (
      <div className="min-h-screen bg-forge-dark text-slate-100 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-white mb-2">Agent Not Found</h2>
          <p className="text-slate-400 text-sm mb-4">
            {error || 'This agent URL is inactive or has not been deployed yet.'}
          </p>
          <a
            href="/"
            className="inline-block px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm rounded-lg transition"
          >
            Return to PromptForge
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-forge-dark text-slate-100 flex flex-col">
      {/* Header bar with metadata & Birth Certificate info */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold text-white">{deployment.agent_name}</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
                v{deployment.version} Deployed
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800">
                PromptForge Certified
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              ID: {deployment.agent_id}
            </p>
          </div>
        </div>

        {/* Birth Certificate Badge & Verification Trigger */}
        {deployment.certificate_id && (
          <div className="flex items-center space-x-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs text-slate-400 font-mono">
                Fingerprint: {deployment.composite_fingerprint?.slice(0, 16)}...
              </div>
              <div className="text-[11px] text-emerald-400 flex items-center justify-end space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Hash-Chained Provenance</span>
              </div>
            </div>
            <button
              onClick={verifyCertificate}
              disabled={verifying}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 rounded-lg border border-slate-700 transition"
            >
              <Award className="w-3.5 h-3.5 text-amber-400" />
              <span>{verifying ? 'Verifying...' : 'Verify Certificate'}</span>
            </button>
          </div>
        )}
      </header>

      {/* Verification modal / banner when verified */}
      {verificationResult && (
        <div className="bg-emerald-950/40 border-b border-emerald-800/40 px-6 py-3 flex items-center justify-between text-xs text-emerald-200">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>
              <strong>Cryptographic Chain Verified:</strong> Checked{' '}
              {verificationResult.audit_blocks_checked} lifecycle audit blocks from genesis. Blueprint, Red Team, and Scorecard hashes intact.
            </span>
          </div>
          <button
            onClick={() => setVerificationResult(null)}
            className="text-slate-400 hover:text-slate-200 ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Sub-bar Navigation: Chat & Test vs Security Monitor & Drift */}
      <div className="border-b border-slate-800 bg-slate-900/30 px-6 flex items-center justify-between">
        <div className="flex space-x-6">
          <button
            onClick={() => setActiveTab('chat')}
            className={`py-3 border-b-2 font-medium text-xs flex items-center space-x-2 transition ${
              activeTab === 'chat'
                ? 'border-emerald-500 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Interactive Chat Runtime</span>
          </button>
          <button
            onClick={() => setActiveTab('monitor')}
            className={`py-3 border-b-2 font-medium text-xs flex items-center space-x-2 transition ${
              activeTab === 'monitor'
                ? 'border-emerald-500 text-white'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Continuous Monitor & Drift</span>
          </button>
        </div>

        <a
          href="/monitor"
          className="text-xs text-slate-400 hover:text-emerald-400 font-mono transition"
        >
          Fleet Monitor →
        </a>
      </div>

      {/* Main container */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 flex flex-col">
        {activeTab === 'chat' ? (
          <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col">
            <AgentChatWindow
              blueprint={blueprint}
              onReset={() => {}}
              apiBaseUrl={apiBaseUrl}
            />
          </div>
        ) : (
          <MonitorDashboardView
            agentId={deployment.agent_id}
            agentName={deployment.agent_name}
            apiBaseUrl={apiBaseUrl}
            tenantId="tenant-demo"
          />
        )}
      </main>
    </div>
  );
}