'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
  Cpu,
  Shield,
  Send,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Terminal,
  RefreshCw,
  Flame,
  Award,
  Swords,
  FileCheck,
  Activity,
  Layers,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Users,
  Search,
  Check,
  Sliders,
  Compass,
  Zap,
  Globe,
  Plus
} from 'lucide-react';

export type ForgeStage =
  | 'input'
  | 'confirm_spec'
  | 'assembling'
  | 'chat'
  | 'redteam'
  | 'harden'
  | 'verify'
  | 'audit'
  | 'monitor'
  | 'evolve'
  | 'arena'
  | 'dossier';

export type SurfaceMode = 'ask' | 'deploy';

export interface UnifiedNavigationShellProps {
  activeStage?: ForgeStage;
  onNavigateStage?: (stage: ForgeStage) => void;
  surface?: SurfaceMode;
  onSurfaceChange?: (surface: SurfaceMode) => void;
  activeTenant?: string;
  onTenantChange?: (tenantId: string) => void;
  pipelineMode?: 'forge' | 'audit';
  onPipelineModeChange?: (mode: 'forge' | 'audit') => void;
  agentName?: string;
  blueprintId?: string;
  compositeScore?: number;
  children?: React.ReactNode;
}

interface ViewItem {
  id: ForgeStage;
  label: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  askEligible: boolean;
  stepNumber: number;
  routeHref?: string;
}

export const ALL_PRODUCT_VIEWS: ViewItem[] = [
  {
    id: 'input',
    label: 'Forge Builder',
    subtitle: '1-sentence prompt decomposition into security policy',
    icon: Cpu,
    color: 'text-blue-400',
    askEligible: true,
    stepNumber: 1,
    routeHref: '/'
  },
  {
    id: 'audit',
    label: 'Audit Explorer',
    subtitle: 'Bring-Your-Own-Agent zero-trust ingestion & certification',
    icon: Shield,
    color: 'text-emerald-400',
    askEligible: false,
    stepNumber: 1,
    routeHref: '/'
  },
  {
    id: 'confirm_spec',
    label: 'Spec Confirmation',
    subtitle: 'Interactive capability & unstated boundary review',
    icon: CheckCircle2,
    color: 'text-cyan-400',
    askEligible: true,
    stepNumber: 2
  },
  {
    id: 'chat',
    label: 'Live Agent Chat',
    subtitle: 'Direct runtime interaction & tool execution inspect',
    icon: Send,
    color: 'text-blue-400',
    askEligible: true,
    stepNumber: 4
  },
  {
    id: 'redteam',
    label: 'Red Team Live',
    subtitle: 'Streaming 3-axis hostile adversarial injection',
    icon: Flame,
    color: 'text-red-400',
    askEligible: false,
    stepNumber: 5
  },
  {
    id: 'harden',
    label: 'Hardening Log',
    subtitle: 'Automated CRISPE diffs & synthesized guardrails',
    icon: RefreshCw,
    color: 'text-amber-400',
    askEligible: false,
    stepNumber: 6
  },
  {
    id: 'verify',
    label: 'Scorecard View',
    subtitle: 'Deterministic 7-metric verification & birth certificate',
    icon: Award,
    color: 'text-emerald-400',
    askEligible: true,
    stepNumber: 7
  },
  {
    id: 'evolve',
    label: 'EVOLVE Lineage',
    subtitle: 'Multi-generation genetic prompt evolution tree',
    icon: Sparkles,
    color: 'text-purple-400',
    askEligible: false,
    stepNumber: 8,
    routeHref: '/evolve'
  },
  {
    id: 'arena',
    label: 'ARENA Sparring',
    subtitle: 'Multi-agent adversarial sparring & seam security',
    icon: Swords,
    color: 'text-rose-400',
    askEligible: false,
    stepNumber: 9,
    routeHref: '/arena'
  },
  {
    id: 'monitor',
    label: 'MONITOR View',
    subtitle: 'Production drift defense & automatic re-hardening',
    icon: Activity,
    color: 'text-teal-400',
    askEligible: false,
    stepNumber: 10,
    routeHref: '/monitor'
  },
  {
    id: 'dossier',
    label: 'DOSSIER Passport',
    subtitle: 'Cryptographic employment record & tamper-evident claims',
    icon: FileCheck,
    color: 'text-indigo-400',
    askEligible: true,
    stepNumber: 11,
    routeHref: '/dossier'
  }
];

const TENANTS = [
  { id: 'tenant-demo', name: 'Demo Sandbox', badge: 'Default' },
  { id: 'tenant-enterprise-acme', name: 'Acme Corp', badge: 'Production' },
  { id: 'tenant-fintech-shield', name: 'Fintech Vault', badge: 'Compliance' }
];

export default function UnifiedNavigationShell({
  activeStage = 'input',
  onNavigateStage,
  surface = 'deploy',
  onSurfaceChange,
  activeTenant = 'tenant-demo',
  onTenantChange,
  pipelineMode = 'forge',
  onPipelineModeChange,
  agentName,
  blueprintId,
  compositeScore,
  children
}: UnifiedNavigationShellProps) {
  const [viewMenuOpen, setViewMenuOpen] = useState(false);
  const [tenantMenuOpen, setTenantMenuOpen] = useState(false);
  const [customTenantInput, setCustomTenantInput] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const viewMenuRef = useRef<HTMLDivElement>(null);
  const tenantMenuRef = useRef<HTMLDivElement>(null);

  // Close menus when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (viewMenuRef.current && !viewMenuRef.current.contains(e.target as Node)) {
        setViewMenuOpen(false);
      }
      if (tenantMenuRef.current && !tenantMenuRef.current.contains(e.target as Node)) {
        setTenantMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter views based on active surface
  const visibleViews = ALL_PRODUCT_VIEWS.filter((v) =>
    surface === 'ask' ? v.askEligible : true
  );

  // Compute pipeline progress percentage
  const stageWeights: Record<ForgeStage, number> = {
    input: 10,
    audit: 15,
    confirm_spec: 25,
    assembling: 35,
    chat: 45,
    redteam: 60,
    harden: 70,
    verify: 80,
    evolve: 88,
    arena: 94,
    dossier: 100,
    monitor: 100
  };
  const currentProgress = stageWeights[activeStage] || 10;

  const currentView = ALL_PRODUCT_VIEWS.find((v) => v.id === activeStage);

  const handleStageClick = (stage: ForgeStage) => {
    setViewMenuOpen(false);
    if (onNavigateStage) {
      onNavigateStage(stage);
    }
  };

  const handleCustomTenantSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customTenantInput.trim() && onTenantChange) {
      onTenantChange(customTenantInput.trim());
      setShowCustomInput(false);
      setTenantMenuOpen(false);
    }
  };

  return (
    <div className="w-full flex flex-col items-center">
      {/* Top Navbar */}
      <header className="w-full max-w-7xl flex flex-col md:flex-row items-center justify-between py-3 px-4 md:px-8 border-b border-[#232D42] bg-[#0B0F17]/90 backdrop-blur-md sticky top-0 z-50 gap-3">
        {/* Brand & Mode Indicators */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <Link href="/" className="flex items-center gap-2.5 group cursor-pointer">
            <div className="p-2 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30 group-hover:border-blue-400 transition-all flex items-center justify-center shadow-lg shadow-blue-500/10">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-black tracking-tight text-white group-hover:text-blue-200 transition-colors">
                  PromptForge
                </span>
                <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  v1.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                The Self-Hardening AI Operating System
              </p>
            </div>
          </Link>

          {/* Surface Indicator Badge */}
          <div className={`hidden lg:flex items-center gap-2 px-3 py-1 rounded-xl border text-xs transition-all ${
            surface === 'ask'
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 shadow-sm shadow-amber-500/5'
              : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300 shadow-sm shadow-cyan-500/5'
          }`}>
            <span className="text-slate-400 font-medium">Audience:</span>
            <span className="font-bold uppercase tracking-wider">
              {surface === 'ask' ? 'Creator & PM (Ask Surface)' : 'Platform & DevOps (Deploy Surface)'}
            </span>
          </div>
        </div>

        {/* Center & Right Controls: Surface Toggle, Tenant Switcher, Quick View Menu */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full md:w-auto justify-end">
          {/* Two-Surface Toggle */}
          <div className="flex items-center p-1 bg-[#121826] border border-[#232D42] rounded-xl shadow-inner">
            <button
              type="button"
              onClick={() => onSurfaceChange && onSurfaceChange('ask')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                surface === 'ask'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Switch to Ask Surface (simplified, outcome-focused for business/non-technical users)"
            >
              <Compass className="w-3.5 h-3.5" />
              Ask Surface
            </button>
            <button
              type="button"
              onClick={() => onSurfaceChange && onSurfaceChange('deploy')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                surface === 'deploy'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20 border border-blue-500'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Switch to Deploy Surface (full technical & cryptographic controls for developers/security)"
            >
              <Sliders className="w-3.5 h-3.5" />
              Deploy Surface
            </button>
          </div>

          {/* Tenant Switcher Dropdown */}
          <div className="relative" ref={tenantMenuRef}>
            <button
              type="button"
              onClick={() => setTenantMenuOpen(!tenantMenuOpen)}
              className="px-2.5 py-1.5 rounded-xl bg-[#121826] border border-[#232D42] hover:border-slate-600 text-xs font-medium text-slate-300 flex items-center gap-2 transition-all shadow-sm"
              title="Active Multi-Tenant Context"
            >
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-mono text-slate-200">{activeTenant}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            </button>

            {tenantMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl bg-[#121826] border border-[#232D42] shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="text-[10px] uppercase font-bold text-slate-400 px-2 py-1 tracking-wider">
                  Select Workspace Tenant
                </div>
                <div className="space-y-1 my-1">
                  {TENANTS.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => {
                        if (onTenantChange) onTenantChange(t.id);
                        setTenantMenuOpen(false);
                      }}
                      className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between transition-colors ${
                        activeTenant === t.id
                          ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30 font-medium'
                          : 'text-slate-300 hover:bg-[#1A2234]'
                      }`}
                    >
                      <div className="flex flex-col">
                        <span className="font-medium text-white">{t.name}</span>
                        <span className="text-[10px] font-mono text-slate-500">{t.id}</span>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {t.badge}
                      </span>
                    </button>
                  ))}
                </div>

                <div className="pt-2 border-t border-[#232D42]">
                  {!showCustomInput ? (
                    <button
                      type="button"
                      onClick={() => setShowCustomInput(true)}
                      className="w-full text-left px-2 py-1 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1.5 font-medium"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Switch to custom tenant...
                    </button>
                  ) : (
                    <form onSubmit={handleCustomTenantSubmit} className="space-y-2 p-1">
                      <input
                        type="text"
                        value={customTenantInput}
                        onChange={(e) => setCustomTenantInput(e.target.value)}
                        placeholder="Enter tenant ID (e.g. tenant-org-1)"
                        className="w-full px-2.5 py-1 text-xs bg-[#0B0F17] border border-[#232D42] rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                        autoFocus
                      />
                      <div className="flex items-center gap-2 justify-end">
                        <button
                          type="button"
                          onClick={() => setShowCustomInput(false)}
                          className="px-2 py-1 text-[10px] text-slate-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-2.5 py-1 text-[10px] bg-blue-600 text-white rounded font-medium hover:bg-blue-500"
                        >
                          Set Tenant
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Quick View Navigator Menu (Single-click access to all 11 views) */}
          <div className="relative" ref={viewMenuRef}>
            <button
              type="button"
              onClick={() => setViewMenuOpen(!viewMenuOpen)}
              className="px-3 py-1.5 rounded-xl bg-blue-600/15 border border-blue-500/30 text-xs font-semibold text-blue-300 hover:bg-blue-600/25 flex items-center gap-2 transition-all shadow-sm"
              title="Quickly jump to any of the 11 PromptForge product views"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Views ({visibleViews.length})</span>
              <ChevronDown className="w-3.5 h-3.5 opacity-75" />
            </button>

            {viewMenuOpen && (
              <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-[#121826] border border-[#232D42] shadow-2xl p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between px-2 py-1.5 border-b border-[#232D42] mb-1">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    {surface === 'ask' ? 'Ask Surface Views' : 'All 11 Product Views'}
                  </span>
                  <span className="text-[10px] font-mono text-blue-400">Single-Click Jump</span>
                </div>

                <div className="max-h-96 overflow-y-auto space-y-1 py-1">
                  {visibleViews.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeStage === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleStageClick(item.id)}
                        className={`w-full text-left px-3 py-2 rounded-xl flex items-start gap-2.5 transition-all ${
                          isActive
                            ? 'bg-blue-600/25 border border-blue-500/40 text-white'
                            : 'text-slate-300 hover:bg-[#1A2234] hover:text-white border border-transparent'
                        }`}
                      >
                        <div className={`p-1.5 rounded-lg bg-[#0F1420] border border-[#232D42] mt-0.5 ${item.color}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold">{item.label}</span>
                            {isActive && (
                              <span className="text-[9px] uppercase font-bold text-emerald-400 flex items-center gap-1">
                                <Check className="w-3 h-3" /> Active
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                            {item.subtitle}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="pt-2 border-t border-[#232D42] flex items-center justify-between text-[11px] px-2 text-slate-500">
                  <span>Standalone Routes:</span>
                  <div className="flex items-center gap-2">
                    <Link href="/monitor" className="text-teal-400 hover:underline flex items-center gap-0.5">
                      Monitor <ExternalLink className="w-2.5 h-2.5" />
                    </Link>
                    <Link href="/arena" className="text-rose-400 hover:underline flex items-center gap-0.5">
                      Arena <ExternalLink className="w-2.5 h-2.5" />
                    </Link>
                    <Link href="/dossier" className="text-indigo-400 hover:underline flex items-center gap-0.5">
                      Dossier <ExternalLink className="w-2.5 h-2.5" />
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Surface Persona Distinction Banner */}
      <div className={`w-full max-w-7xl px-4 md:px-8 py-2.5 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs transition-all ${
        surface === 'ask'
          ? 'bg-amber-950/25 border-amber-500/30 text-amber-200'
          : 'bg-blue-950/25 border-cyan-500/30 text-cyan-200'
      }`}>
        <div className="flex items-center gap-2.5">
          <div className={`p-1.5 rounded-lg border flex items-center justify-center shrink-0 ${
            surface === 'ask'
              ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 shadow-sm shadow-amber-500/10'
              : 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300 shadow-sm shadow-cyan-500/10'
          }`}>
            {surface === 'ask' ? <Compass className="w-4 h-4" /> : <Terminal className="w-4 h-4" />}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold tracking-wide uppercase text-[11px]">
                {surface === 'ask' ? 'Ask Surface — Creator & Product Studio' : 'Deploy Surface — Platform & Security Console'}
              </span>
              <span className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-mono font-bold ${
                surface === 'ask' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              }`}>
                {surface === 'ask' ? 'Creator Mode (PM/Domain Lead)' : 'Engineering Mode (DevOps/SecOps)'}
              </span>
            </div>
            <p className="text-[11px] opacity-80 mt-0.5">
              {surface === 'ask'
                ? 'Serving the person who described the agent: Natural language intent, plain-English boundary review, conversational testing, and executive safety scorecards.'
                : 'Serving the engineer who certifies and integrates the agent: Raw CRISPE prompt architecture, OpenAI tool schemas, surgical hardening diffs, HTTP API endpoints, and cryptographic tamper-evident ledgers.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
          <button
            type="button"
            onClick={() => onSurfaceChange && onSurfaceChange(surface === 'ask' ? 'deploy' : 'ask')}
            className={`px-3 py-1 rounded-lg font-semibold text-[11px] border transition-all ${
              surface === 'ask'
                ? 'bg-amber-500/15 hover:bg-amber-500/25 border-amber-500/40 text-amber-300 shadow-sm'
                : 'bg-cyan-500/15 hover:bg-cyan-500/25 border-cyan-500/40 text-cyan-300 shadow-sm'
            }`}
          >
            Switch to {surface === 'ask' ? 'Deploy Surface →' : 'Ask Surface →'}
          </button>
        </div>
      </div>

      {/* Unified Breadcrumb Strip & Progress Bar */}
      <div className={`w-full max-w-7xl px-4 md:px-8 py-3 border-b flex flex-col gap-2 transition-all ${
        surface === 'ask' ? 'bg-[#0E0F14]/60 border-amber-500/15' : 'bg-[#0B0F17]/50 border-[#1A2234]'
      }`}>
        {/* Progress Bar */}
        <div className="w-full flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-300">
              {surface === 'ask' ? 'Creator Milestone Progress:' : 'Pipeline Progression:'}
            </span>
            <span className={`font-mono font-bold ${surface === 'ask' ? 'text-amber-400' : 'text-blue-400'}`}>
              {currentProgress}%
            </span>
            {agentName && (
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium text-[11px] ml-1">
                Agent: {agentName}
              </span>
            )}
            {compositeScore !== undefined && compositeScore !== null && (
              <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 font-bold text-[11px]">
                Score: {compositeScore}/100
              </span>
            )}
          </div>

          <div className="hidden sm:flex items-center gap-2 text-[11px] text-slate-500">
            <span>
              {surface === 'ask'
                ? 'Showing 4 business milestone stages'
                : 'Showing all 11 technical engineering stages'}
            </span>
          </div>
        </div>

        {/* Progress Fill Track */}
        <div className="w-full h-1.5 bg-[#151C2C] rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ease-out ${
              surface === 'ask'
                ? 'bg-gradient-to-r from-amber-500 via-amber-400 to-emerald-400'
                : 'bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400'
            }`}
            style={{ width: `${currentProgress}%` }}
          />
        </div>

        {/* Breadcrumb Steps (Dynamic based on surface) */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1 text-xs font-medium no-scrollbar">
          {visibleViews.map((step, idx) => {
            const isActive = activeStage === step.id;
            const Icon = step.icon;

            const activeClass = surface === 'ask'
              ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/30'
              : 'bg-blue-600 text-white font-bold shadow-md shadow-blue-600/30';

            const inactiveClass = surface === 'ask'
              ? 'bg-[#151412] text-amber-200/70 hover:text-amber-100 hover:bg-[#1E1C18] border border-amber-500/20'
              : 'bg-[#121826] text-slate-400 hover:text-slate-200 hover:bg-[#1A2234] border border-[#232D42]';

            return (
              <React.Fragment key={step.id}>
                {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />}
                <button
                  type="button"
                  onClick={() => handleStageClick(step.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg shrink-0 transition-all ${
                    isActive ? activeClass : inactiveClass
                  }`}
                  title={step.subtitle}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? (surface === 'ask' ? 'text-slate-950' : 'text-white') : step.color}`} />
                  <span>{step.label}</span>
                </button>
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Children content (if wrapped) */}
      {children && <div className="w-full max-w-7xl p-4 md:p-8">{children}</div>}
    </div>
  );
}
