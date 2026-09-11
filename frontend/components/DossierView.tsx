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

import { apiFetch } from '../lib/api';

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
      const res = await apiFetch(`${API_BASE_URL}/api/blueprints/summary`, {}, tenantId);
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
      const res = await apiFetch(`${API_BASE_URL}/api/dossier/${agentId}`, {}, tenantId);
      if (res.ok) {
        const data = await res.json();
        setDossier(data);
      } else {
        // Try assembling fresh
        const assembleRes = await apiFetch(`${API_BASE_URL}/api/dossier/${agentId}/assemble`, {
          method: 'POST',
        }, tenantId);
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
      const res = await apiFetch(`${API_BASE_URL}/api/dossier/${dossier.agent_id}/claims/${claimId}/verify`, {}, tenantId);
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
    <div className="w-full max-w-7xl mx-auto space-y-6 text-[#3D3229] font-sans">
      {/* Header & Agent Selector */}
      <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-2xl p-6 shadow-card relative overflow-hidden">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-[#C75A3B]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="p-2.5 rounded-xl bg-[#C75A3B]/10 border border-[#C75A3B]/20 text-[#C75A3B]">
                <FileCheck className="w-6 h-6" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-black tracking-tight text-[#3D3229]">Agent Dossier & Employment Record</h2>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#C75A3B]/10 text-[#C75A3B] border border-[#C75A3B]/20 uppercase tracking-wide">
                    Phase 12 Verifiable Proof
                  </span>
                </div>
                <p className="text-xs text-[#666555]">
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
                  className="bg-[#F0E6DC]/60 border border-[#E8DDD2] text-sm text-[#3D3229] font-medium rounded-xl px-3.5 py-2 pr-8 appearance-none focus:outline-none focus:ring-2 focus:ring-[#C75A3B]/20 focus:border-[#C75A3B] hover:border-[#D97D5E] transition cursor-pointer"
                >
                  {availableAgents.map((ag) => (
                    <option key={ag.blueprint_id} value={ag.blueprint_id}>
                      {ag.agent_name} ({ag.blueprint_id.slice(0, 8)})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-[#666555] absolute right-2.5 top-3 pointer-events-none" />
              </div>
            )}

            <button
              onClick={() => loadDossier(selectedAgentId)}
              disabled={loading || !selectedAgentId}
              className="px-3.5 py-2 rounded-xl bg-[#F0E6DC] hover:bg-[#E8DDD2] border border-[#E8DDD2] text-sm font-semibold text-[#3D3229] flex items-center gap-2 transition shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Dossier</span>
            </button>

            {dossier && (
              <button
                onClick={verifyAllClaims}
                disabled={batchVerifying || loading}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#C75A3B] to-[#D97D5E] hover:from-[#B84A2F] hover:to-[#C75A3B] text-white text-sm font-bold shadow-md hover:shadow-lg flex items-center gap-2 transition disabled:opacity-50"
              >
                <ShieldCheck className={`w-4 h-4 ${batchVerifying ? 'animate-spin' : ''}`} />
                <span>{batchVerifying ? 'Verifying All Claims...' : 'Verify All Claims'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="mt-4 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {dossier ? (
        <>
          {/* Agent Passport Summary Card */}
          <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-2xl p-6 shadow-card relative overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Profile info */}
              <div className="md:col-span-2 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#C75A3B] to-[#D97D5E] flex items-center justify-center font-black text-lg text-white shadow-md">
                    {dossier.agent_name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-[#3D3229]">{dossier.agent_name}</h3>
                    <div className="flex items-center gap-2 text-xs text-[#666555]">
                      <span className="font-mono">{dossier.domain}</span>
                      <span>•</span>
                      <span>v{dossier.version}</span>
                      <span>•</span>
                      <span className="font-mono text-[#C75A3B] font-semibold">{dossier.agent_id.slice(0, 12)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#F0E6DC]/60 border border-[#E8DDD2] text-[#3D3229]">
                    <Fingerprint className="w-3.5 h-3.5 text-[#C75A3B]" />
                    <span>Watermark: <strong className="font-mono text-[#3D3229]">{dossier.provenance.watermark}</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#F0E6DC]/60 border border-[#E8DDD2] text-[#3D3229]">
                    <Lock className="w-3.5 h-3.5 text-[#2ECC71]" />
                    <span>Forger: <span className="font-medium text-[#3D3229]">{dossier.provenance.forger_identity}</span></span>
                  </div>
                </div>

                {/* Overarching Dossier Hash */}
                {dossier.dossier_hash && (
                  <div className="p-2.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate">
                      <ShieldCheck className="w-4 h-4 text-[#2ECC71] shrink-0" />
                      <span className="text-[#666555]">Root Dossier Digest:</span>
                      <span className="font-mono text-[#3D3229] font-semibold truncate">{dossier.dossier_hash}</span>
                    </div>
                    <button
                      onClick={() => copyToClipboard(dossier.dossier_hash || '', 'dossier_hash')}
                      className="ml-2 text-[#666555] hover:text-[#3D3229] transition p-1"
                      title="Copy Dossier Hash"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* High-Level Scorecards */}
              <div className="md:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex flex-col justify-between hover:border-[#D97D5E]/40 transition">
                  <span className="text-[11px] font-semibold text-[#666555] flex items-center gap-1">
                    <Award className="w-3.5 h-3.5 text-[#C75A3B]" />
                    Composite Score
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-black text-[#3D3229]">{dossier.security_record.promptforge_score}</span>
                    <span className="text-xs text-[#9C9288]">/ 100</span>
                  </div>
                  <span className="text-[10px] text-[#2ECC71] mt-1 font-bold">Deterministic Spine Verified</span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex flex-col justify-between hover:border-[#D97D5E]/40 transition">
                  <span className="text-[11px] font-semibold text-[#666555] flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5 text-[#C75A3B]" />
                    Survival Rate
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-black text-[#3D3229]">
                      {Math.round(dossier.security_record.redteam_survival_rate * 100)}%
                    </span>
                  </div>
                  <span className="text-[10px] text-[#666555] mt-1 font-medium">
                    {dossier.security_record.attacks_blocked}/{dossier.security_record.total_attacks_faced} Attacks Blocked
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex flex-col justify-between hover:border-[#D97D5E]/40 transition">
                  <span className="text-[11px] font-semibold text-[#666555] flex items-center gap-1">
                    <Swords className="w-3.5 h-3.5 text-[#D97D5E]" />
                    ARENA Defense
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-black text-[#3D3229]">
                      {dossier.security_record.arena_sparring.arena_security_score}
                    </span>
                    <span className="text-xs text-[#9C9288]">/ 100</span>
                  </div>
                  <span className="text-[10px] text-[#666555] mt-1 font-medium">
                    {dossier.security_record.arena_sparring.pairings_defended}/{dossier.security_record.arena_sparring.total_pairings} Sparrings
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex flex-col justify-between hover:border-[#D97D5E]/40 transition">
                  <span className="text-[11px] font-semibold text-[#666555] flex items-center gap-1">
                    <Dna className="w-3.5 h-3.5 text-[#C75A3B]" />
                    EVOLVE Lineage
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-lg font-black text-[#3D3229]">
                      {dossier.lineage.is_evolved ? `Gen ${dossier.lineage.generation}` : 'Genesis'}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#666555] mt-1 truncate">
                    {dossier.lineage.strategy}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex flex-col justify-between hover:border-[#D97D5E]/40 transition">
                  <span className="text-[11px] font-semibold text-[#666555] flex items-center gap-1">
                    <Activity className="w-3.5 h-3.5 text-[#2ECC71]" />
                    Runtime Monitor
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className={`text-lg font-black ${dossier.security_record.runtime_monitoring.drift_detected ? 'text-red-600' : 'text-[#2ECC71]'}`}>
                      {dossier.security_record.runtime_monitoring.drift_detected ? 'Drift Alert' : 'Active'}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#666555] mt-1 font-medium">
                    {dossier.security_record.runtime_monitoring.total_monitor_runs} Runs Logged
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] flex flex-col justify-between hover:border-[#D97D5E]/40 transition">
                  <span className="text-[11px] font-semibold text-[#666555] flex items-center gap-1">
                    <Lock className="w-3.5 h-3.5 text-[#D97D5E]" />
                    Birth Certificate
                  </span>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-xs font-mono font-bold text-[#3D3229] truncate">
                      {dossier.provenance.birth_certificate_id || 'CERT-PENDING'}
                    </span>
                  </div>
                  <span className="text-[10px] text-[#666555] mt-1 font-medium">Hash-Chain Anchored</span>
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-[#E8DDD2] gap-2 overflow-x-auto pb-1 text-sm font-medium">
            <button
              onClick={() => setActiveTab('claims')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'claims'
                  ? 'bg-[#C75A3B] text-white shadow-sm font-semibold'
                  : 'bg-[#F0E6DC]/60 text-[#666555] hover:text-[#3D3229] hover:bg-[#F0E6DC] border border-[#E8DDD2]'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Verifiable Claims Ledger ({dossier.claims.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'security'
                  ? 'bg-[#C75A3B] text-white shadow-sm font-semibold'
                  : 'bg-[#F0E6DC]/60 text-[#666555] hover:text-[#3D3229] hover:bg-[#F0E6DC] border border-[#E8DDD2]'
              }`}
            >
              <Swords className="w-4 h-4" />
              <span>Security & Sparring History</span>
            </button>

            <button
              onClick={() => setActiveTab('capabilities')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'capabilities'
                  ? 'bg-[#C75A3B] text-white shadow-sm font-semibold'
                  : 'bg-[#F0E6DC]/60 text-[#666555] hover:text-[#3D3229] hover:bg-[#F0E6DC] border border-[#E8DDD2]'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Verified Capabilities ({dossier.capabilities.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('lineage')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'lineage'
                  ? 'bg-[#C75A3B] text-white shadow-sm font-semibold'
                  : 'bg-[#F0E6DC]/60 text-[#666555] hover:text-[#3D3229] hover:bg-[#F0E6DC] border border-[#E8DDD2]'
              }`}
            >
              <Dna className="w-4 h-4" />
              <span>EVOLVE Lineage</span>
            </button>

            <button
              onClick={() => setActiveTab('provenance')}
              className={`px-4 py-2.5 rounded-xl flex items-center gap-2 transition ${
                activeTab === 'provenance'
                  ? 'bg-[#C75A3B] text-white shadow-sm font-semibold'
                  : 'bg-[#F0E6DC]/60 text-[#666555] hover:text-[#3D3229] hover:bg-[#F0E6DC] border border-[#E8DDD2]'
              }`}
            >
              <Fingerprint className="w-4 h-4" />
              <span>Cryptographic Provenance</span>
            </button>
          </div>

          {/* TAB 1: Verifiable Claims Ledger */}
          {activeTab === 'claims' && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl bg-[#F0E6DC]/40 border border-[#E8DDD2] text-xs text-[#666555]">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-[#C75A3B] shrink-0" />
                  <span>
                    Each claim below is anchored to a cryptographic artifact on the hash chain. Click <strong className="text-[#3D3229]">Verify Claim</strong> to execute an independent live check against the immutable database hash.
                  </span>
                </div>
                <div className="relative w-full sm:w-64">
                  <Search className="w-3.5 h-3.5 text-[#9C9288] absolute left-3 top-2.5 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filter claims..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[#FBF8F4] border border-[#E8DDD2] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[#3D3229] placeholder-[#9C9288] focus:outline-none focus:ring-2 focus:ring-[#C75A3B]/20 focus:border-[#C75A3B]"
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
                        className="bg-[#FBF8F4] border border-[#E8DDD2] hover:border-[#C75A3B]/40 rounded-xl p-4 transition shadow-card"
                      >
                        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                          <div className="space-y-1.5 flex-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                  claim.claim_type === 'capability'
                                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                    : claim.claim_type === 'security'
                                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                    : claim.claim_type === 'lineage'
                                    ? 'bg-purple-50 text-purple-700 border border-purple-200'
                                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                }`}
                              >
                                {claim.claim_type}
                              </span>
                              <span className="font-mono text-xs text-[#666555]">{claim.claim_id}</span>
                              <span className="text-[#9C9288]">•</span>
                              <span className="text-xs text-[#666555] font-mono">Ref: {claim.underlying_artifact_id}</span>
                            </div>

                            <p className="text-sm font-bold text-[#3D3229]">{claim.statement}</p>

                            <div className="flex items-center gap-2 text-xs text-[#666555]">
                              <span>Evidence Hash:</span>
                              <span className="font-mono text-[#3D3229] bg-[#F0E6DC]/60 px-2 py-0.5 rounded border border-[#E8DDD2]">
                                {claim.evidence_hash.slice(0, 20)}...{claim.evidence_hash.slice(-8)}
                              </span>
                              <button
                                onClick={() => copyToClipboard(claim.evidence_hash, claim.claim_id)}
                                className="text-[#9C9288] hover:text-[#3D3229] transition"
                                title="Copy Evidence Hash"
                              >
                                <Copy className="w-3.5 h-3.5" />
                              </button>
                              {copiedText === claim.claim_id && (
                                <span className="text-[10px] text-[#2ECC71] font-bold">Copied!</span>
                              )}
                            </div>
                          </div>

                          {/* Verification Button & Status */}
                          <div className="flex items-center gap-3 shrink-0">
                            {result ? (
                              <div
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold ${
                                  result.is_valid
                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                                    : 'bg-red-50 border-red-200 text-red-700'
                                }`}
                              >
                                {result.is_valid ? (
                                  <>
                                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                    <span>Verified Against Hash Chain</span>
                                  </>
                                ) : (
                                  <>
                                    <XCircle className="w-4 h-4 text-red-600" />
                                    <span>Hash Mismatch / Tampered</span>
                                  </>
                                )}
                              </div>
                            ) : null}

                            <button
                              onClick={() => verifyClaimIndependently(claim.claim_id)}
                              disabled={isVerifying}
                              className="px-3 py-1.5 rounded-lg bg-[#F0E6DC] hover:bg-[#E8DDD2] border border-[#E8DDD2] text-[#3D3229] hover:text-[#C75A3B] text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
                              <span>{isVerifying ? 'Verifying...' : result ? 'Re-Verify' : 'Verify Claim'}</span>
                            </button>
                          </div>
                        </div>

                        {/* Detailed Verification Outcome if Checked */}
                        {result && (
                          <div className="mt-3 pt-3 border-t border-[#E8DDD2] text-xs flex flex-col gap-1 text-[#666555]">
                            <div className="flex items-center justify-between">
                              <span className="text-[#666555] font-medium">Live Verification Details:</span>
                              <span className="text-[#9C9288]">{new Date(result.checked_at).toLocaleTimeString()}</span>
                            </div>
                            <p className="font-mono text-[#3D3229]">{result.verification_details}</p>
                            <div className="flex items-center gap-2 font-mono text-[11px] text-[#666555] mt-1">
                              <span>Computed Live Hash:</span>
                              <span className="text-[#3D3229] bg-[#F0E6DC] px-1.5 py-0.5 rounded border border-[#E8DDD2] font-semibold">
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
              <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-5 space-y-3 shadow-card">
                <h4 className="text-base font-bold text-[#3D3229] flex items-center gap-2">
                  <Shield className="w-4 h-4 text-[#C75A3B]" />
                  <span>3-Axis Red Team Defense Survival Record</span>
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-center">
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <div className="text-2xl font-black text-[#3D3229]">{dossier.security_record.total_attacks_faced}</div>
                    <div className="text-xs text-[#666555] font-medium">Total Attacks Faced</div>
                  </div>
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <div className="text-2xl font-black text-[#2ECC71]">{dossier.security_record.attacks_blocked}</div>
                    <div className="text-xs text-[#666555] font-medium">Attacks Blocked</div>
                  </div>
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <div className="text-2xl font-black text-red-600">{dossier.security_record.attacks_compromised}</div>
                    <div className="text-xs text-[#666555] font-medium">Compromised</div>
                  </div>
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <div className="text-2xl font-black text-[#C75A3B]">
                      {Math.round(dossier.security_record.redteam_survival_rate * 100)}%
                    </div>
                    <div className="text-xs text-[#666555] font-medium">Survival Rate</div>
                  </div>
                </div>
              </div>

              {/* Hardening Patches Applied */}
              <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-5 space-y-3 shadow-card">
                <h4 className="text-base font-bold text-[#3D3229] flex items-center gap-2">
                  <Lock className="w-4 h-4 text-[#D97D5E]" />
                  <span>Applied Hardening Patches ({dossier.security_record.applied_patches.length})</span>
                </h4>
                {dossier.security_record.applied_patches.length > 0 ? (
                  <div className="space-y-3">
                    {dossier.security_record.applied_patches.map((patch) => (
                      <div key={patch.patch_id} className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2] space-y-1 text-xs text-[#3D3229]">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[#C75A3B] font-bold">{patch.patch_id}</span>
                          <span className="text-[#666555]">{new Date(patch.applied_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-[#3D3229]">
                          <strong>Target:</strong> {patch.target_guardrail} • <strong>Vulnerability:</strong> {patch.vulnerability_addressed}
                        </p>
                        <pre className="p-2.5 rounded-lg bg-[#3D3229] text-[#2ECC71] font-mono text-[11px] overflow-x-auto whitespace-pre-wrap border border-[#E8DDD2]">
                          {patch.patch_rule}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#666555]">Zero patches required. Agent passed all adversarial baselines on initial compilation.</p>
                )}
              </div>

              {/* ARENA Sparring Ring Outcomes */}
              <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-5 space-y-3 shadow-card">
                <h4 className="text-base font-bold text-[#3D3229] flex items-center gap-2">
                  <Swords className="w-4 h-4 text-[#D97D5E]" />
                  <span>ARENA Multi-Agent Sparring & Seam Defense</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <span className="text-[#666555] font-medium">Pairings Defended</span>
                    <p className="text-xl font-black text-[#3D3229] mt-1">
                      {dossier.security_record.arena_sparring.pairings_defended} / {dossier.security_record.arena_sparring.total_pairings}
                    </p>
                  </div>
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <span className="text-[#666555] font-medium">Seam Attacks Intercepted</span>
                    <p className="text-xl font-black text-[#2ECC71] mt-1">
                      {dossier.security_record.arena_sparring.seam_attacks_intercepted}
                    </p>
                  </div>
                  <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                    <span className="text-[#666555] font-medium">Arena Security Score</span>
                    <p className="text-xl font-black text-[#C75A3B] mt-1">
                      {dossier.security_record.arena_sparring.arena_security_score} / 100
                    </p>
                  </div>
                </div>

                {dossier.security_record.arena_sparring.hostile_personas_faced.length > 0 && (
                  <div className="pt-2 text-xs">
                    <span className="text-[#666555] font-medium">Hostile Personas Faced:</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {dossier.security_record.arena_sparring.hostile_personas_faced.map((p) => (
                        <span key={p} className="px-2 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-700 font-mono text-[11px] font-semibold">
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
                  <div key={cap.capability_id} className="bg-[#FBF8F4] border border-[#E8DDD2] hover:border-[#C75A3B]/40 rounded-xl p-4 space-y-2 shadow-card transition">
                    <div className="flex items-center justify-between">
                      <span className="font-black text-[#3D3229] text-base">{cap.name}</span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 border border-emerald-200 text-emerald-700">
                        {Math.round(cap.success_rate * 100)}% Pass Rate
                      </span>
                    </div>
                    <p className="text-xs text-[#666555]">{cap.description}</p>
                    <div className="pt-2 border-t border-[#E8DDD2] text-[11px] text-[#666555] space-y-1">
                      <p><strong className="text-[#3D3229]">Verification:</strong> {cap.verification_method}</p>
                      <p><strong className="text-[#3D3229]">Evidence:</strong> {cap.evidence_summary}</p>
                      {cap.claim_hash && (
                        <p className="font-mono text-[#9C9288] truncate">Digest: {cap.claim_hash}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: EVOLVE Lineage */}
          {activeTab === 'lineage' && (
            <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-6 space-y-4 shadow-card">
              <h4 className="text-base font-bold text-[#3D3229] flex items-center gap-2">
                <Dna className="w-5 h-5 text-[#C75A3B]" />
                <span>Deep Forge (EVOLVE) Lineage Record</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                  <span className="text-[#666555] font-medium">Evolution Status</span>
                  <p className="text-lg font-black text-[#3D3229] mt-1">
                    {dossier.lineage.is_evolved ? 'Evolved Champion' : 'Genesis Compilation'}
                  </p>
                </div>
                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                  <span className="text-[#666555] font-medium">Generation</span>
                  <p className="text-lg font-black text-[#C75A3B] mt-1">
                    Generation {dossier.lineage.generation}
                  </p>
                </div>
                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2]">
                  <span className="text-[#666555] font-medium">Fitness Score</span>
                  <p className="text-lg font-black text-[#2ECC71] mt-1">
                    {dossier.lineage.fitness_score ? `${dossier.lineage.fitness_score.toFixed(1)} / 100` : 'Baseline'}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#F0E6DC]/40 border border-[#E8DDD2] text-xs space-y-2 text-[#3D3229]">
                <p><strong>Strategy:</strong> <span className="font-mono text-[#3D3229]">{dossier.lineage.strategy}</span></p>
                {dossier.lineage.parent_candidate_ids.length > 0 && (
                  <p><strong>Parent Candidates:</strong> <span className="font-mono text-[#C75A3B]">{dossier.lineage.parent_candidate_ids.join(', ')}</span></p>
                )}
                {dossier.lineage.lineage_log_hash && (
                  <p className="truncate"><strong>Lineage Hash Chain:</strong> <span className="font-mono text-[#666555]">{dossier.lineage.lineage_log_hash}</span></p>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: Provenance & Certificate */}
          {activeTab === 'provenance' && (
            <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-6 space-y-4 shadow-card">
              <h4 className="text-base font-bold text-[#3D3229] flex items-center gap-2">
                <Fingerprint className="w-5 h-5 text-[#C75A3B]" />
                <span>Cryptographic Provenance & Birth Certificate</span>
              </h4>

              <div className="space-y-3 text-xs">
                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2] flex items-center justify-between">
                  <span className="text-[#666555] font-medium">Birth Certificate ID</span>
                  <span className="font-mono text-[#3D3229] font-bold">{dossier.provenance.birth_certificate_id || 'CERT-N/A'}</span>
                </div>

                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2] space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[#666555] font-medium">Composite Fingerprint</span>
                    <button
                      onClick={() => copyToClipboard(dossier.provenance.birth_certificate_fingerprint || '', 'fingerprint')}
                      className="text-[#666555] hover:text-[#3D3229]"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="font-mono text-[#C75A3B] font-semibold break-all">{dossier.provenance.birth_certificate_fingerprint || 'PENDING'}</p>
                </div>

                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2] flex items-center justify-between">
                  <span className="text-[#666555] font-medium">Registry ID</span>
                  <span className="font-mono text-[#3D3229] font-semibold">{dossier.provenance.registry_id}</span>
                </div>

                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2] flex items-center justify-between">
                  <span className="text-[#666555] font-medium">System Prompt Marker</span>
                  <span className="font-mono text-[#3D3229] font-semibold">{dossier.provenance.system_prompt_marker}</span>
                </div>

                <div className="p-3 bg-[#F0E6DC]/40 rounded-lg border border-[#E8DDD2] flex items-center justify-between">
                  <span className="text-[#666555] font-medium">Provenance Hash</span>
                  <span className="font-mono text-[#666555] truncate max-w-xs">{dossier.provenance.provenance_hash}</span>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="bg-[#FBF8F4] border border-[#E8DDD2] rounded-2xl p-12 text-center space-y-4 shadow-card">
          <FileCheck className="w-12 h-12 text-[#9C9288] mx-auto" />
          <h3 className="text-lg font-black text-[#3D3229]">No Agent Dossier Selected</h3>
          <p className="text-sm text-[#666555] max-w-md mx-auto">
            Select an agent from the dropdown above or enter an agent ID to inspect its verifiable employment record.
          </p>
        </div>
      )}
    </div>
  );
}
