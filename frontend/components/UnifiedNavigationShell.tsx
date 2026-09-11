'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
  Cpu,
  Shield,
  Send,
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Flame,
  Award,
  Swords,
  FileCheck,
  Activity,
  Layers,
  ChevronDown,
  ExternalLink,
  Check,
  Sliders,
  Compass,
  Plus,
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
    routeHref: '/',
  },
  {
    id: 'audit',
    label: 'Audit Explorer',
    subtitle: 'Bring-Your-Own-Agent zero-trust ingestion & certification',
    icon: Shield,
    color: 'text-emerald-400',
    askEligible: false,
    stepNumber: 1,
    routeHref: '/',
  },
  {
    id: 'confirm_spec',
    label: 'Spec Confirmation',
    subtitle: 'Interactive capability & unstated boundary review',
    icon: CheckCircle2,
    color: 'text-cyan-400',
    askEligible: true,
    stepNumber: 2,
  },
  {
    id: 'chat',
    label: 'Live Agent Chat',
    subtitle: 'Direct runtime interaction & tool execution inspect',
    icon: Send,
    color: 'text-blue-400',
    askEligible: true,
    stepNumber: 4,
  },
  {
    id: 'redteam',
    label: 'Red Team Live',
    subtitle: 'Streaming 3-axis hostile adversarial injection',
    icon: Flame,
    color: 'text-red-400',
    askEligible: false,
    stepNumber: 5,
  },
  {
    id: 'harden',
    label: 'Hardening Log',
    subtitle: 'Automated CRISPE diffs & synthesized guardrails',
    icon: RefreshCw,
    color: 'text-amber-400',
    askEligible: false,
    stepNumber: 6,
  },
  {
    id: 'verify',
    label: 'Scorecard View',
    subtitle: 'Deterministic 7-metric verification & birth certificate',
    icon: Award,
    color: 'text-emerald-400',
    askEligible: true,
    stepNumber: 7,
  },
  {
    id: 'evolve',
    label: 'EVOLVE Lineage',
    subtitle: 'Multi-generation genetic prompt evolution tree',
    icon: Sparkles,
    color: 'text-purple-400',
    askEligible: false,
    stepNumber: 8,
    routeHref: '/evolve',
  },
  {
    id: 'arena',
    label: 'ARENA Sparring',
    subtitle: 'Multi-agent adversarial sparring & seam security',
    icon: Swords,
    color: 'text-rose-400',
    askEligible: false,
    stepNumber: 9,
    routeHref: '/arena',
  },
  {
    id: 'monitor',
    label: 'MONITOR View',
    subtitle: 'Production drift defense & automatic re-hardening',
    icon: Activity,
    color: 'text-teal-400',
    askEligible: false,
    stepNumber: 10,
    routeHref: '/monitor',
  },
  {
    id: 'dossier',
    label: 'DOSSIER Passport',
    subtitle: 'Cryptographic employment record & tamper-evident claims',
    icon: FileCheck,
    color: 'text-indigo-400',
    askEligible: true,
    stepNumber: 11,
    routeHref: '/dossier',
  },
];

const TENANTS = [
  { id: 'tenant-demo', name: 'Demo Sandbox', badge: 'Default' },
  { id: 'tenant-enterprise-acme', name: 'Acme Corp', badge: 'Production' },
  { id: 'tenant-fintech-shield', name: 'Fintech Vault', badge: 'Compliance' },
];

const SURFACE_COPY: Record<SurfaceMode, { label: string; audience: string }> = {
  ask: { label: 'Ask Surface', audience: 'Creator & PM' },
  deploy: { label: 'Deploy Surface', audience: 'Platform & DevSecOps' },
};

export default function UnifiedNavigationShell({
  activeStage = 'input',
  onNavigateStage,
  surface = 'deploy',
  onSurfaceChange,
  activeTenant = 'tenant-demo',
  onTenantChange,
  agentName,
  compositeScore,
  children,
}: UnifiedNavigationShellProps) {
  const [viewMenuOpen, setViewMenuOpen] = useState(false);
  const [tenantMenuOpen, setTenantMenuOpen] = useState(false);
  const [customTenantInput, setCustomTenantInput] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const viewMenuRef = useRef<HTMLDivElement>(null);
  const tenantMenuRef = useRef<HTMLDivElement>(null);

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

  const visibleViews = ALL_PRODUCT_VIEWS.filter((v) => (surface === 'ask' ? v.askEligible : true));

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
    monitor: 100,
  };
  const currentProgress = stageWeights[activeStage] || 10;
  const currentView = ALL_PRODUCT_VIEWS.find((v) => v.id === activeStage);
  const CurrentIcon = currentView?.icon || Cpu;
  const stepIndex = Math.max(1, visibleViews.findIndex((v) => v.id === activeStage) + 1);

  const handleStageClick = (stage: ForgeStage) => {
    setViewMenuOpen(false);
    onNavigateStage?.(stage);
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
      {/* Top bar — one row: brand, current-view pill, surface toggle, tenant, views menu */}
      <header className="w-full max-w-7xl flex flex-wrap items-center gap-3 py-3 px-4 md:px-8 border-b border-forge-border bg-forge-dark/90 backdrop-blur-md sticky top-0 z-50">
        <Link href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="w-8 h-8 flex items-center justify-center rounded-lg bg-blue-600/15 text-blue-400 border border-blue-500/25 group-hover:border-blue-400/60 transition-colors">
            <Cpu className="w-4 h-4" />
          </div>
          <span className="text-[15px] font-bold tracking-tight text-white group-hover:text-blue-200 transition-colors">
            PromptForge
          </span>
        </Link>

        {/* Current view pill — click opens the full view menu (also visible below on scroll via progress row) */}
        <button
          type="button"
          onClick={() => setViewMenuOpen((v) => !v)}
          className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-lg border border-forge-border bg-forge-surface/70 text-xs text-slate-300 hover:border-slate-600 transition-colors"
        >
          <CurrentIcon className={`w-3.5 h-3.5 ${currentView?.color || 'text-blue-400'}`} />
          <span className="font-medium text-slate-200">{currentView?.label || 'Forge Builder'}</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-500">Step {stepIndex} of {visibleViews.length}</span>
        </button>

        <div className="flex-1" />

        <div className="flex items-center gap-2 flex-wrap justify-end">
          {/* Surface segmented toggle */}
          <div className="flex items-center p-0.5 bg-forge-surface border border-forge-border rounded-lg">
            <button
              type="button"
              onClick={() => onSurfaceChange?.('ask')}
              className={`px-2.5 py-1 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                surface === 'ask' ? 'bg-amber-500/20 text-amber-300' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Ask Surface — simplified, outcome-focused view for business & product users"
            >
              <Compass className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Ask</span>
            </button>
            <button
              type="button"
              onClick={() => onSurfaceChange?.('deploy')}
              className={`px-2.5 py-1 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                surface === 'deploy' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Deploy Surface — full technical & cryptographic controls for engineers"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Deploy</span>
            </button>
          </div>

          {/* Tenant switcher */}
          <div className="relative" ref={tenantMenuRef}>
            <button
              type="button"
              onClick={() => setTenantMenuOpen((v) => !v)}
              className="px-2.5 py-1.5 rounded-lg bg-forge-surface border border-forge-border hover:border-slate-600 text-xs font-medium text-slate-300 flex items-center gap-1.5 transition-colors"
              title="Active tenant"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="font-mono text-slate-200 max-w-[9rem] truncate">{activeTenant}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            </button>

            {tenantMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl bg-forge-surface border border-forge-border shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="text-[10px] uppercase font-bold text-slate-500 px-2 py-1 tracking-wider">
                  Select workspace tenant
                </div>
                <div className="space-y-1 my-1">
                  {TENANTS.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => {
                        onTenantChange?.(t.id);
                        setTenantMenuOpen(false);
                      }}
                      className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs flex items-center justify-between transition-colors ${
                        activeTenant === t.id
                          ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30 font-medium'
                          : 'text-slate-300 hover:bg-forge-surface2'
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
                <div className="pt-2 border-t border-forge-border">
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
                        placeholder="e.g. tenant-org-1"
                        className="w-full px-2.5 py-1 text-xs bg-forge-dark border border-forge-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
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
                          Set tenant
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Views menu — the single place to jump to any of the 11 views */}
          <div className="relative" ref={viewMenuRef}>
            <button
              type="button"
              onClick={() => setViewMenuOpen((v) => !v)}
              className="px-2.5 py-1.5 rounded-lg bg-blue-600/15 border border-blue-500/25 text-xs font-medium text-blue-300 hover:bg-blue-600/25 flex items-center gap-1.5 transition-colors"
              title="Jump to any PromptForge view"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Views</span>
              <ChevronDown className="w-3.5 h-3.5 opacity-75" />
            </button>

            {viewMenuOpen && (
              <div className="absolute right-0 mt-2 w-80 rounded-xl bg-forge-surface border border-forge-border shadow-2xl p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between px-2 py-1.5 border-b border-forge-border mb-1">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    {surface === 'ask' ? 'Ask surface views' : `All ${ALL_PRODUCT_VIEWS.length} product views`}
                  </span>
                  <span className="text-[10px] font-mono text-blue-400">1-click jump</span>
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
                        className={`w-full text-left px-3 py-2 rounded-lg flex items-start gap-2.5 transition-colors ${
                          isActive
                            ? 'bg-blue-600/20 border border-blue-500/30 text-white'
                            : 'text-slate-300 hover:bg-forge-surface2 border border-transparent'
                        }`}
                      >
                        <div className={`p-1.5 rounded-md bg-forge-dark border border-forge-border mt-0.5 ${item.color}`}>
                          <Icon className="w-3.5 h-3.5" />
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
                          <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{item.subtitle}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="pt-2 border-t border-forge-border flex items-center justify-between text-[11px] px-2 text-slate-500">
                  <span>Standalone routes:</span>
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

      {/* Slim progress row — replaces the old triple-stacked banner + full breadcrumb chip row */}
      <div className="w-full max-w-7xl px-4 md:px-8 py-2 border-b border-forge-borderSoft bg-forge-dark/50 flex items-center gap-3 text-[11px] text-slate-500">
        <span className={`shrink-0 font-medium ${surface === 'ask' ? 'text-amber-400' : 'text-blue-400'}`}>
          {SURFACE_COPY[surface].label}
        </span>
        <span className="hidden sm:inline shrink-0">· {SURFACE_COPY[surface].audience}</span>
        <div className="flex-1 h-1 bg-[#151C2C] rounded-full overflow-hidden min-w-[3rem]">
          <div
            className={`h-full transition-all duration-500 ease-out ${
              surface === 'ask'
                ? 'bg-gradient-to-r from-amber-500 to-emerald-400'
                : 'bg-gradient-to-r from-blue-600 to-cyan-400'
            }`}
            style={{ width: `${currentProgress}%` }}
          />
        </div>
        <span className="shrink-0 font-mono">{currentProgress}%</span>
        {agentName && (
          <span className="hidden md:inline shrink-0 px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700 font-medium">
            {agentName}
          </span>
        )}
        {compositeScore !== undefined && compositeScore !== null && (
          <span className="hidden md:inline shrink-0 px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 font-bold">
            Score {compositeScore}/100
          </span>
        )}
      </div>

      {children && <div className="w-full max-w-7xl p-4 md:p-8">{children}</div>}
    </div>
  );
}
