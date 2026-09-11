'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Award,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Copy,
  Lock,
  Dna,
  Swords,
  Activity,
  Fingerprint,
  Sparkles,
  RefreshCw,
  Search,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Shield,
  FileCheck,
  ArrowRight,
} from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DossierCapabilityRecord {
  capability_id: string;
  name: string;
  description: string;
  verification_method: string;
  success_rate: number;
  evidence_summary: string;
  underlying_test_count: number;
  claim_hash?: string;
}

export interface DossierPatchRecord {
  patch_id: string;
  target_guardrail: string;
  vulnerability_addressed: string;
  patch_rule: string;
  applied_at: string;
}

export interface DossierArenaRecord {
  total_pairings: number;
  pairings_defended: number;
  hostile_personas_faced: string[];
  seam_attacks_intercepted: number;
  arena_security_score: number;
  cross_agent_playbook_entries_contributed: number;
  last_sparring_timestamp?: string;
}

export interface DossierMonitorRecord {
  drift_detected: boolean;
  total_monitor_runs: number;
  alerts_triggered: number;
  alerts_resolved: number;
  active_schedule_count: number;
  last_monitored_at?: string;
}

export interface DossierSecurityRecord {
  redteam_survival_rate: number;
  total_attacks_faced: number;
  attacks_blocked: number;
  attacks_compromised: number;
  promptforge_score: number;
  applied_patches: DossierPatchRecord[];
  arena_sparring: DossierArenaRecord;
  runtime_monitoring: DossierMonitorRecord;
}

export interface DossierLineageRecord {
  is_evolved: boolean;
  generation: number;
  strategy: string;
  parent_candidate_ids: string[];
  fitness_score?: number;
  lineage_log_hash?: string;
}

export interface DossierProvenanceRecord {
  forger_identity: string;
  tenant_id: string;
  registry_id: string;
  watermark: string;
  system_prompt_marker: string;
  provenance_hash: string;
  birth_certificate_id?: string;
  birth_certificate_fingerprint?: string;
  registered_at: string;
}

export interface DossierVerifiableClaim {
  claim_id: string;
  claim_type: 'capability' | 'security' | 'lineage' | 'provenance';
  statement: string;
  underlying_artifact_id: string;
  evidence_hash: string;
  is_verified: boolean;
}

export interface AgentDossierData {
  dossier_id: string;
  agent_id: string;
  blueprint_id: string;
  spec_id: string;
  agent_name: string;
  domain: string;
  version: number;
  capabilities: DossierCapabilityRecord[];
  security_record: DossierSecurityRecord;
  lineage: DossierLineageRecord;
  provenance: DossierProvenanceRecord;
  claims: DossierVerifiableClaim[];
  dossier_hash?: string;
  created_at: string;
}

export interface ClaimVerificationResult {
  claim_id: string;
  is_valid: boolean;
  claim_type: string;
  statement: string;
  underlying_artifact_id: string;
  evidence_hash: string;
  computed_live_hash: string;
  verification_details: string;
  checked_at: string;
}

interface DossierViewProps {
  agentId?: string;
  initialDossier?: AgentDossierData | null;
  tenantId?: string;
}

export default function DossierView({
  agentId: initialAgentId,
  initialDossier,
  tenantId = 'tenant-demo'
}: DossierViewProps) {
  const [selectedAgentId, setSelectedAgentId] = useState<string>(initialAgentId || '');
  const [dossier, setDossier] = useState<AgentDossierData | null>(initialDossier || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'claims' | 'security' | 'capabilities' | 'lineage' | 'provenance'>('claims');

  // Independent Claim Verification State
  const [verifyingClaimId, setVerifyingClaimId] = useState<string | null>(null);
  const [claimResults, setClaimResults] = useState<Record<string, ClaimVerificationResult>>({});
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [batchVerifying, setBatchVerifying] = useState<boolean>(false);

  // Available blueprints for quick switcher
  const [availableAgents, setAvailableAgents] = useState<{ blueprint_id: string; agent_name: string }[]>([]);

  useEffect(() => {
    fetchAvailableAgents();
  }, []);

  useEffect(() => {
    if (initialAgentId) {
      setSelectedAgentId(initialAgentId);
      loadDossier(initialAgentId);
    }
  }, [initialAgentId]);

  const fetchAvailableAgents = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/blueprints/summary`, {
        headers: { 'X-Tenant-ID': tenantId },
      });
      if (res.ok) {
        const data = await res.json();
        setAvailableAgents(data);
        if (!selectedAgentId && data.length > 0) {
          setSelectedAgentId(data[0].blueprint_id);
          loadDossier(data[0].blueprint_id);
        }
      }
    } catch {
      // Ignore initial load error
    }
  };

  const loadDossier = async (agentId: string) => {
    if (!agentId) return;
    setLoading(true);
    setError(null);
    setClaimResults({});
    try {
      const res = await fetch(`${API_BASE_URL}/api/dossier/${agentId}`, {
        headers: { 'X-Tenant-ID': tenantId },
      });
      if (res.ok) {
        const data = await res.json();
        setDossier(data);
      } else {
        // Try assembling fresh
        const assembleRes = await fetch(`${API_BASE_URL}/api/dossier/${agentId}/assemble`, {
          method: 'POST',
          headers: { 'X-Tenant-ID': tenantId },
        });
        if (assembleRes.ok) {
          const assembled = await assembleRes.json();
          setDossier(assembled);
        } else {
          const errData = await assembleRes.json().catch(() => ({ detail: 'Failed to load dossier' }));
          setError(errData.detail || 'Could not assemble agent dossier.');
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to PromptForge backend.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const verifyClaimIndependently = async (claimId: string) => {
    if (!dossier) return;
    setVerifyingClaimId(claimId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/dossier/${dossier.agent_id}/claims/${claimId}/verify`, {
        headers: { 'X-Tenant-ID': tenantId },
      });
      if (res.ok) {
        const result: ClaimVerificationResult = await res.json();
        setClaimResults((prev) => ({ ...prev, [claimId]: result }));
      } else {
        const errJson = await res.json().catch(() => ({ detail: 'Verification failed' }));
        setClaimResults((prev) => ({
          ...prev,
          [claimId]: {
            claim_id: claimId,
            is_valid: false,
            claim_type: 'unknown',
            statement: 'Verification error',
            underlying_artifact_id: '',
            evidence_hash: '',
            computed_live_hash: 'ERROR',
            verification_details: errJson.detail || 'Failed to verify against hash chain.',
            checked_at: new Date().toISOString(),
          },
        }));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Network error during verification.';
      setClaimResults((prev) => ({
        ...prev,
        [claimId]: {
          claim_id: claimId,
          is_valid: false,
          claim_type: 'unknown',
          statement: 'Network failure',
          underlying_artifact_id: '',
          evidence_hash: '',
          computed_live_hash: 'ERROR',
          verification_details: msg,
          checked_at: new Date().toISOString(),
        },
      }));
    } finally {
      setVerifyingClaimId(null);
    }
  };

  const verifyAllClaims = async () => {
    if (!dossier || !dossier.claims.length) return;
    setBatchVerifying(true);
    for (const claim of dossier.claims) {
      await verifyClaimIndependently(claim.claim_id);
    }
    setBatchVerifying(false);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 text-slate-100 font-sans">
      {/* Header & Agent Selector */}
      <div className="bg-[#0E131F] border border-slate-800/80 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="p-2 rounded-xl bg-indigo-950/80 border border-indigo-700/40 text-indigo-400">
                <FileCheck className="w-6 h-6" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-bold tracking-tight text-white">Agent Dossier & Employment Record</h2>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wide">
                    Phase 12 Verifiable Proof
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Cryptographically verified history covering capabilities, survival record, evolutionary lineage, and hash chain provenance.
                </p>
              </div>
            </div>
          </div>

          {/* Selector & Actions */}
          <div className="flex flex-wrap items-center gap-3">
            {availableAgents.length > 0 && (
              <div className="relative">
                <select
                  value={selectedAgentId}
                  onChange={(e) => {
                    setSelectedAgentId(e.target.value);
                    loadDossier(e.target.value);
                  }}
                  className="bg-slate-900 border border-slate-700/80 text-sm text-slate-200 rounded-xl px-3.5 py-2 pr-8 appearance-none focus:outline-none focus:border-indigo-500 hover:border-slate-600 transition cursor-pointer"
                >
                  {availableAgents.map((ag) => (
                    <option key={ag.blueprint_id} value={ag.blueprint_id}>
                      {ag.agent_name} ({ag.blueprint_id.slice(0, 8)})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
              </div>
            )}

            <button
              onClick={() => loadDossier(selectedAgentId)}
              disabled={loading || !selectedAgentId}
              className="px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-sm font-medium text-slate-200 flex items-center gap-2 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Dossier</span>
            </button>

            {dossier && (
              <button
                onClick={verifyAllClaims}
                disabled={batchVerifying || loading}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-sm font-semibold shadow-lg shadow-indigo-900/30 flex items-center gap-2 transition disabled:opacity-50"
              >
                <ShieldCheck className={`w-4 h-4 ${batchVerifying ? 'animate-spin' : ''}`} />
                <span>{batchVerifying ? 'Verifying All Claims...' : 'Verify All Claims'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="mt-4 p-3.5 rounded-xl bg-red-950/60 border border-red-800/50 text-red-200 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {dossier ? (
        <>
          {/* Agent Passport Summary Card */}
          <div className="bg-[#0B0F19] border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Profile info */}
              <div className="md:col-span-2 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-600 flex items-center justify-center font-bold text-lg text-white shadow-md">
                    {dossier.agent_name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">{dossier.agent_name}</h3>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span className="font-mono">{dossier.domain}</span>
                      <span>•</span>
                      <span>v{dossier.version}</span>
                      <span>•</span>
                      <span className="font-mono text-indigo-400">{dossier.agent_id.slice(0, 12)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
                    <Fingerprint className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Watermark: <strong className="font-mono text-white">{dossier.provenance.watermark}</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
                    <Lock className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Forger: <span className="text-slate-200">{dossier.provenance.forger_identity}</span></span>
                  </div>
                </div>

                {/* Overarching Dossier Hash */}
                {dossier.dossier_hash && (
                  <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span className="text-slate-400">Root Dossier Digest:</span>
                      <span className="font-mono text-slate-200 truncate">{dossier.dossier_hash}</span>
                    </div>
                    <button
                      onClick={() => copyToClipboard(dossier.dossier_hash || '', 'dossier_hash')}
                      className="ml-2 text-slate-400 hover:text-white transition"
                      title="Copy Dossier Hash"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* High-Level Scorecards */}
              <div className="md:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Award className="w-3.5 h-3.5 text-blue-400" />
                    Composite Score
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-black text-white">{dossier.security_record.promptforge_score}</span>
                    <span className="text-xs text-slate-500">/ 100</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 mt-1 font-medium">Deterministic Spine Verified</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5 text-red-400" />
                    Survival Rate
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-black text-white">
                      {Math.round(dossier.security_record.redteam_survival_rate * 100)}%
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1">
                    {dossier.security_record.attacks_blocked}/{dossier.security_record.total_attacks_faced} Attacks Blocked
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Swords className="w-3.5 h-3.5 text-amber-400" />
                    ARENA Defense
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-black text-white">
                      {dossier.security_record.arena_sparring.arena_security_score}
                    </span>
                    <span className="text-xs text-slate-500">/ 100</span>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1">
                    {dossier.security_record.arena_sparring.pairings_defended}/{dossier.security_record.arena_sparring.total_pairings} Sparrings
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Dna className="w-3.5 h-3.5 text-purple-400" />
                    EVOLVE Lineage
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-lg font-bold text-white">
                      {dossier.lineage.is_evolved ? `Gen ${dossier.lineage.generation}` : 'Genesis'}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1 truncate">
                    {dossier.lineage.strategy}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Activity className="w-3.5 h-3.5 text-emerald-400" />
                    Runtime Monitor
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-lg font-bold text-emerald-400">
                      {dossier.security_record.runtime_monitoring.drift_detected ? 'Drift Alert' : 'Active'}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1">
                    {dossier.security_record.runtime_monitoring.total_monitor_runs} Runs Logged
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
                  <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Lock className="w-3.5 h-3.5 text-cyan-400" />
                    Birth Certificate
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-xs font-mono text-cyan-300 truncate">
                      {dossier.provenance.birth_certificate_id || 'CERT-PENDING'}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1">Hash-Chain Anchored</span>
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-800 gap-2 overflow-x-auto pb-1 text-sm font-medium">
            <button
              onClick={() => setActiveTab('claims')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'claims'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Verifiable Claims Ledger ({dossier.claims.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'security'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Swords className="w-4 h-4" />
              <span>Security & Sparring History</span>
            </button>

            <button
              onClick={() => setActiveTab('capabilities')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'capabilities'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Verified Capabilities ({dossier.capabilities.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('lineage')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'lineage'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Dna className="w-4 h-4" />
              <span>EVOLVE Lineage</span>
            </button>

            <button
              onClick={() => setActiveTab('provenance')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'provenance'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Fingerprint className="w-4 h-4" />
              <span>Cryptographic Provenance</span>
            </button>
          </div>

          {/* TAB 1: Verifiable Claims Ledger (Headline Feature of Step 95) */}
          {activeTab === 'claims' && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
                  <span>
                    Each claim below is anchored to a cryptographic artifact on the hash chain. Click <strong>Verify Claim</strong> to execute an independent live check against the immutable database hash.
                  </span>
                </div>
                <div className="relative w-full sm:w-64">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filter claims..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3.5">
                {dossier.claims
                  .filter((c) =>
                    !searchQuery ||
                    c.statement.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    c.claim_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    c.claim_type.toLowerCase().includes(searchQuery.toLowerCase())
                  )
                  .map((claim) => {
                    const result = claimResults[claim.claim_id];
                    const isVerifying = verifyingClaimId === claim.claim_id;

                    return (
                      <div
                        key={claim.claim_id}
                        className="bg-[#0D121F] border border-slate-800/90 hover:border-slate-700/80 rounded-xl p-4 transition shadow-md"
                      >
                        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                          <div className="space-y-1.5 flex-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                  claim.claim_type === 'capability'
                                    ? 'bg-blue-900/60 text-blue-300 border border-blue-700/50'
                                    : claim.claim_type === 'security'
                                    ? 'bg-red-900/60 text-red-300 border border-red-700/50'
                                    : claim.claim_type === 'lineage'
                                    ? 'bg-purple-900/60 text-purple-300 border border-purple-700/50'
                                    : 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50'
                                }`}
                              >
                                {claim.claim_type}
                              </span>
                              <span className="font-mono text-xs text-slate-400">{claim.claim_id}</span>
                              <span className="text-slate-600">•</span>
                              <span className="text-xs text-slate-400 font-mono">Ref: {claim.underlying_artifact_id}</span>
                            </div>

                            <p className="text-sm font-medium text-slate-100">{claim.statement}</p>

                            <div className="flex items-center gap-2 text-xs text-slate-400">
                              <span>Evidence Hash:</span>
                              <span className="font-mono text-slate-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                                {claim.evidence_hash.slice(0, 20)}...{claim.evidence_hash.slice(-8)}
                              </span>
                              <button
                                onClick={() => copyToClipboard(claim.evidence_hash, claim.claim_id)}
                                className="text-slate-500 hover:text-slate-300"
                                title="Copy Evidence Hash"
                              >
                                <Copy className="w-3.5 h-3.5" />
                              </button>
                              {copiedText === claim.claim_id && (
                                <span className="text-[10px] text-emerald-400">Copied!</span>
                              )}
                            </div>
                          </div>

                          {/* Verification Button & Status */}
                          <div className="flex items-center gap-3 shrink-0">
                            {result ? (
                              <div
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                                  result.is_valid
                                    ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300'
                                    : 'bg-red-950/60 border-red-800/60 text-red-300'
                                }`}
                              >
                                {result.is_valid ? (
                                  <>
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                    <span>Verified Against Hash Chain</span>
                                  </>
                                ) : (
                                  <>
                                    <XCircle className="w-4 h-4 text-red-400" />
                                    <span>Hash Mismatch / Tampered</span>
                                  </>
                                )}
                              </div>
                            ) : null}

                            <button
                              onClick={() => verifyClaimIndependently(claim.claim_id)}
                              disabled={isVerifying}
                              className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 hover:text-indigo-200 text-xs font-medium flex items-center gap-1.5 transition disabled:opacity-50"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
                              <span>{isVerifying ? 'Verifying...' : result ? 'Re-Verify' : 'Verify Claim'}</span>
                            </button>
                          </div>
                        </div>

                        {/* Detailed Verification Outcome if Checked */}
                        {result && (
                          <div className="mt-3 pt-3 border-t border-slate-800/70 text-xs flex flex-col gap-1 text-slate-300">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400">Live Verification Details:</span>
                              <span className="text-slate-500">{new Date(result.checked_at).toLocaleTimeString()}</span>
                            </div>
                            <p className="font-mono text-slate-300">{result.verification_details}</p>
                            <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400 mt-1">
                              <span>Computed Live Hash:</span>
                              <span className="text-indigo-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                                {result.computed_live_hash.slice(0, 24)}...
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* TAB 2: Security & Sparring History */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              {/* Red Team Metrics */}
              <div className="bg-[#0D121F] border border-slate-800 rounded-xl p-5 space-y-3">
                <h4 className="text-base font-bold text-white flex items-center gap-2">
                  <Shield className="w-4 h-4 text-red-400" />
                  <span>3-Axis Red Team Defense Survival Record</span>
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-center">
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-2xl font-black text-white">{dossier.security_record.total_attacks_faced}</div>
                    <div className="text-xs text-slate-400">Total Attacks Faced</div>
                  </div>
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-2xl font-black text-emerald-400">{dossier.security_record.attacks_blocked}</div>
                    <div className="text-xs text-slate-400">Attacks Blocked</div>
                  </div>
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-2xl font-black text-red-400">{dossier.security_record.attacks_compromised}</div>
                    <div className="text-xs text-slate-400">Compromised</div>
                  </div>
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <div className="text-2xl font-black text-blue-400">
                      {Math.round(dossier.security_record.redteam_survival_rate * 100)}%
                    </div>
                    <div className="text-xs text-slate-400">Survival Rate</div>
                  </div>
                </div>
              </div>

              {/* Hardening Patches Applied */}
              <div className="bg-[#0D121F] border border-slate-800 rounded-xl p-5 space-y-3">
                <h4 className="text-base font-bold text-white flex items-center gap-2">
                  <Lock className="w-4 h-4 text-amber-400" />
                  <span>Applied Hardening Patches ({dossier.security_record.applied_patches.length})</span>
                </h4>
                {dossier.security_record.applied_patches.length > 0 ? (
                  <div className="space-y-3">
                    {dossier.security_record.applied_patches.map((patch) => (
                      <div key={patch.patch_id} className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-amber-300 font-bold">{patch.patch_id}</span>
                          <span className="text-slate-400">{new Date(patch.applied_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-slate-300">
                          <strong>Target:</strong> {patch.target_guardrail} • <strong>Vulnerability:</strong> {patch.vulnerability_addressed}
                        </p>
                        <pre className="p-2 rounded bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap border border-slate-800/80">
                          {patch.patch_rule}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">Zero patches required. Agent passed all adversarial baselines on initial compilation.</p>
                )}
              </div>

              {/* ARENA Sparring Ring Outcomes */}
              <div className="bg-[#0D121F] border border-slate-800 rounded-xl p-5 space-y-3">
                <h4 className="text-base font-bold text-white flex items-center gap-2">
                  <Swords className="w-4 h-4 text-amber-400" />
                  <span>ARENA Multi-Agent Sparring & Seam Defense</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-slate-400">Pairings Defended</span>
                    <p className="text-xl font-bold text-white mt-1">
                      {dossier.security_record.arena_sparring.pairings_defended} / {dossier.security_record.arena_sparring.total_pairings}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-slate-400">Seam Attacks Intercepted</span>
                    <p className="text-xl font-bold text-emerald-400 mt-1">
                      {dossier.security_record.arena_sparring.seam_attacks_intercepted}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-slate-400">Arena Security Score</span>
                    <p className="text-xl font-bold text-blue-400 mt-1">
                      {dossier.security_record.arena_sparring.arena_security_score} / 100
                    </p>
                  </div>
                </div>

                {dossier.security_record.arena_sparring.hostile_personas_faced.length > 0 && (
                  <div className="pt-2 text-xs">
                    <span className="text-slate-400">Hostile Personas Faced:</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {dossier.security_record.arena_sparring.hostile_personas_faced.map((p) => (
                        <span key={p} className="px-2 py-0.5 rounded bg-red-950/60 border border-red-800/40 text-red-300 font-mono text-[11px]">
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: Verified Capabilities */}
          {activeTab === 'capabilities' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {dossier.capabilities.map((cap) => (
                  <div key={cap.capability_id} className="bg-[#0D121F] border border-slate-800 rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-base">{cap.name}</span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-950 border border-emerald-800 text-emerald-300">
                        {Math.round(cap.success_rate * 100)}% Pass Rate
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">{cap.description}</p>
                    <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                      <p><strong>Verification:</strong> {cap.verification_method}</p>
                      <p><strong>Evidence:</strong> {cap.evidence_summary}</p>
                      {cap.claim_hash && (
                        <p className="font-mono text-slate-500 truncate">Digest: {cap.claim_hash}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: EVOLVE Lineage */}
          {activeTab === 'lineage' && (
            <div className="bg-[#0D121F] border border-slate-800 rounded-xl p-6 space-y-4">
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Dna className="w-5 h-5 text-purple-400" />
                <span>Deep Forge (EVOLVE) Lineage Record</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Evolution Status</span>
                  <p className="text-lg font-bold text-white mt-1">
                    {dossier.lineage.is_evolved ? 'Evolved Champion' : 'Genesis Compilation'}
                  </p>
                </div>
                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Generation</span>
                  <p className="text-lg font-bold text-purple-400 mt-1">
                    Generation {dossier.lineage.generation}
                  </p>
                </div>
                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Fitness Score</span>
                  <p className="text-lg font-bold text-emerald-400 mt-1">
                    {dossier.lineage.fitness_score ? `${dossier.lineage.fitness_score.toFixed(1)} / 100` : 'Baseline'}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs space-y-2">
                <p><strong>Strategy:</strong> <span className="font-mono text-slate-200">{dossier.lineage.strategy}</span></p>
                {dossier.lineage.parent_candidate_ids.length > 0 && (
                  <p><strong>Parent Candidates:</strong> <span className="font-mono text-indigo-300">{dossier.lineage.parent_candidate_ids.join(', ')}</span></p>
                )}
                {dossier.lineage.lineage_log_hash && (
                  <p className="truncate"><strong>Lineage Hash Chain:</strong> <span className="font-mono text-slate-400">{dossier.lineage.lineage_log_hash}</span></p>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: Provenance & Certificate */}
          {activeTab === 'provenance' && (
            <div className="bg-[#0D121F] border border-slate-800 rounded-xl p-6 space-y-4">
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <Fingerprint className="w-5 h-5 text-indigo-400" />
                <span>Cryptographic Provenance & Birth Certificate</span>
              </h4>

              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Birth Certificate ID</span>
                  <span className="font-mono text-white font-bold">{dossier.provenance.birth_certificate_id || 'CERT-N/A'}</span>
                </div>

                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Composite Fingerprint</span>
                    <button
                      onClick={() => copyToClipboard(dossier.provenance.birth_certificate_fingerprint || '', 'fingerprint')}
                      className="text-slate-500 hover:text-white"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="font-mono text-indigo-300 break-all">{dossier.provenance.birth_certificate_fingerprint || 'PENDING'}</p>
                </div>

                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Registry ID</span>
                  <span className="font-mono text-slate-200">{dossier.provenance.registry_id}</span>
                </div>

                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">System Prompt Marker</span>
                  <span className="font-mono text-slate-200">{dossier.provenance.system_prompt_marker}</span>
                </div>

                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Provenance Hash</span>
                  <span className="font-mono text-slate-400 truncate max-w-xs">{dossier.provenance.provenance_hash}</span>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-[#0B0F19] border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <FileCheck className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-white">No Agent Dossier Selected</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Select an agent from the dropdown above or enter an agent ID to inspect its verifiable employment record.
          </p>
        </div>
      )}
    </div>
  );
}
