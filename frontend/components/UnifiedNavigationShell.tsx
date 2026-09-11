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
    color: 'text-[#C75A3B]',
    askEligible: true,
    stepNumber: 1,
    routeHref: '/',
  },
  {
    id: 'audit',
    label: 'Audit Explorer',
    subtitle: 'Bring-Your-Own-Agent zero-trust ingestion & certification',
    icon: Shield,
    color: 'text-[#2ECC71]',
    askEligible: false,
    stepNumber: 1,
    routeHref: '/',
  },
  {
    id: 'confirm_spec',
    label: 'Spec Confirmation',
    subtitle: 'Interactive capability & unstated boundary review',
    icon: CheckCircle2,
    color: 'text-[#D97D5E]',
    askEligible: true,
    stepNumber: 2,
  },
  {
    id: 'chat',
    label: 'Live Agent Chat',
    subtitle: 'Multi-turn delimited sandbox testing with runtime guards',
    icon: Send,
    color: 'text-[#C75A3B]',
    askEligible: true,
    stepNumber: 3,
  },
  {
    id: 'redteam',
    label: 'Red Team Studio',
    subtitle: 'Multi-turn adversarial jailbreak & injection suite',
    icon: Flame,
    color: 'text-[#E74C3C]',
    askEligible: false,
    stepNumber: 4,
  },
  {
    id: 'harden',
    label: 'Hardening Engine',
    subtitle: 'Automated guardrail synthesis & system prompt patching',
    icon: RefreshCw,
    color: 'text-[#F39C12]',
    askEligible: false,
    stepNumber: 5,
  },
  {
    id: 'verify',
    label: 'Verification Scorecard',
    subtitle: 'Five-pillar certification & cryptographic birth certificate',
    icon: Award,
    color: 'text-[#2ECC71]',
    askEligible: true,
    stepNumber: 6,
  },
  {
    id: 'evolve',
    label: 'Deep Forge Lineage',
    subtitle: 'Evolutionary prompt optimization across generations',
    icon: Sparkles,
    color: 'text-[#C75A3B]',
    askEligible: false,
    stepNumber: 7,
  },
  {
    id: 'arena',
    label: 'Model Arena',
    subtitle: 'Head-to-head LLM sparring & seam security evaluation',
    icon: Swords,
    color: 'text-[#D97D5E]',
    askEligible: false,
    stepNumber: 8,
    routeHref: '/arena',
  },
  {
    id: 'dossier',
    label: 'Agent Dossier',
    subtitle: 'Verifiable employment record & tamper-evident audit history',
    icon: FileCheck,
    color: 'text-[#666555]',
    askEligible: false,
    stepNumber: 9,
    routeHref: '/dossier',
  },
  {
    id: 'monitor',
    label: 'Drift Monitor',
    subtitle: 'Production telemetry, anomaly detection, & runtime defense',
    icon: Activity,
    color: 'text-[#2ECC71]',
    askEligible: false,
    stepNumber: 10,
    routeHref: '/monitor',
  },
];

const TENANTS = [
  { id: 'tenant-demo', name: 'Demo Workspace', badge: 'Default' },
  { id: 'tenant-acme', name: 'Acme Corp FinSec', badge: 'Enterprise' },
  { id: 'tenant-sandbox', name: 'Adversarial Lab', badge: 'Isolated' },
];

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
    harden: 72,
    verify: 82,
    evolve: 88,
    arena: 94,
    dossier: 98,
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
      {/* 64px Header Component (Section 4.1) */}
      <header className="w-full h-16 bg-[#F0E6DC] border-b border-[#E8DDD2] sticky top-0 z-50 px-4 md:px-8 flex items-center justify-between gap-4 shadow-sm">
        {/* Logo: "Prompt" in #C75A3B, "Forge" in #D97D5E */}
        <Link href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-[#C75A3B] text-white shadow-md group-hover:bg-[#B84A2F] transition-all">
            <Cpu className="w-5 h-5" />
          </div>
          <span className="text-lg font-bold tracking-tight">
            <span className="text-[#C75A3B]">Prompt</span>
            <span className="text-[#D97D5E]">Forge</span>
          </span>
        </Link>

        {/* Center: Step Indicator & Progress Bar (Section 4.6) */}
        <div className="hidden md:flex items-center gap-3 px-4 py-1.5 rounded-full bg-[#FBF8F4] border border-[#E8DDD2] shadow-sm">
          <button
            type="button"
            onClick={() => setViewMenuOpen((v) => !v)}
            className="flex items-center gap-2 text-xs font-semibold text-[#3D3229] hover:text-[#C75A3B] transition-colors"
          >
            <CurrentIcon className={`w-4 h-4 ${currentView?.color || 'text-[#C75A3B]'}`} />
            <span>Step {stepIndex} of {visibleViews.length}</span>
            <span className="text-[#9B8B7E]">·</span>
            <span className="font-medium text-[#666555]">{currentView?.label || 'Forge Builder'}</span>
          </button>

          {/* Progress Bar with #C75A3B to #2ECC71 Gradient */}
          <div className="w-24 h-1.5 bg-[#E8DDD2] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-[#C75A3B] to-[#2ECC71]"
              style={{ width: `${currentProgress}%` }}
            />
          </div>
          <span className="text-[11px] font-mono font-semibold text-[#666555]">{currentProgress}%</span>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2.5">
          {/* Surface Toggle (Ask vs Deploy) */}
          <div className="flex items-center p-0.5 bg-[#FBF8F4] border border-[#E8DDD2] rounded-lg text-xs font-medium">
            <button
              type="button"
              onClick={() => onSurfaceChange?.('ask')}
              className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                surface === 'ask'
                  ? 'bg-[#F0E6DC] text-[#C75A3B] font-bold shadow-xs'
                  : 'text-[#666555] hover:text-[#3D3229]'
              }`}
              title="Ask Surface: Creator & PM View"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Ask</span>
            </button>
            <button
              type="button"
              onClick={() => onSurfaceChange?.('deploy')}
              className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                surface === 'deploy'
                  ? 'bg-[#C75A3B] text-white font-bold shadow-sm'
                  : 'text-[#666555] hover:text-[#3D3229]'
              }`}
              title="Deploy Surface: Security & DevOps View"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Deploy</span>
            </button>
          </div>

          {/* Tenant Switcher */}
          <div className="relative" ref={tenantMenuRef}>
            <button
              type="button"
              onClick={() => setTenantMenuOpen((v) => !v)}
              className="px-3 py-1.5 rounded-lg bg-[#FBF8F4] border border-[#E8DDD2] hover:border-[#C75A3B] text-xs font-semibold text-[#3D3229] flex items-center gap-1.5 transition-colors shadow-xs"
            >
              <span className="w-2 h-2 rounded-full bg-[#2ECC71]" />
              <span className="font-mono text-[#3D3229] max-w-[8rem] truncate">{activeTenant}</span>
              <ChevronDown className="w-3.5 h-3.5 text-[#9B8B7E]" />
            </button>

            {tenantMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl bg-[#FBF8F4] border border-[#E8DDD2] shadow-card-hover p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="text-[10px] uppercase font-bold text-[#9B8B7E] px-2 py-1 tracking-wider">
                  Active Workspace
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
                          ? 'bg-[#F0E6DC] text-[#C75A3B] border border-[#C75A3B]/30 font-bold'
                          : 'text-[#3D3229] hover:bg-[#F0E6DC]'
                      }`}
                    >
                      <div className="flex flex-col">
                        <span className="font-semibold text-[#3D3229]">{t.name}</span>
                        <span className="text-[10px] font-mono text-[#9B8B7E]">{t.id}</span>
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-white text-[#666555] border border-[#E8DDD2]">
                        {t.badge}
                      </span>
                    </button>
                  ))}
                </div>
                <div className="pt-2 border-t border-[#E8DDD2]">
                  {!showCustomInput ? (
                    <button
                      type="button"
                      onClick={() => setShowCustomInput(true)}
                      className="w-full text-left px-2 py-1 text-xs text-[#C75A3B] hover:text-[#B84A2F] flex items-center gap-1.5 font-semibold"
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
                        className="w-full px-2.5 py-1 text-xs bg-white border border-[#E8DDD2] rounded-lg text-[#3D3229] placeholder-[#9B8B7E] focus:outline-none focus:border-[#C75A3B]"
                        autoFocus
                      />
                      <div className="flex items-center gap-2 justify-end">
                        <button
                          type="button"
                          onClick={() => setShowCustomInput(false)}
                          className="px-2 py-1 text-[10px] text-[#666555] hover:text-[#3D3229]"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-2.5 py-1 text-[10px] btn-primary"
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

          {/* Stages Menu */}
          <div className="relative" ref={viewMenuRef}>
            <button
              type="button"
              onClick={() => setViewMenuOpen((v) => !v)}
              className="px-3 py-1.5 rounded-lg bg-[#FBF8F4] border border-[#E8DDD2] hover:border-[#C75A3B] text-xs font-semibold text-[#C75A3B] flex items-center gap-1.5 transition-all shadow-xs"
              title="1-Click Jump to any Forge Stage"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Stages</span>
              <ChevronDown className="w-3 h-3 opacity-80" />
            </button>

            {viewMenuOpen && (
              <div className="absolute right-0 mt-2 w-80 rounded-xl bg-[#FBF8F4] border border-[#E8DDD2] shadow-card-hover p-2.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between px-2 py-1.5 border-b border-[#E8DDD2] mb-1">
                  <span className="text-[10px] uppercase font-bold text-[#9B8B7E] tracking-wider">
                    {surface === 'ask' ? 'Ask Surface Views' : `All ${ALL_PRODUCT_VIEWS.length} Evaluation Stages`}
                  </span>
                  <span className="text-[10px] font-mono text-[#C75A3B] font-bold">Quick Jump</span>
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
                            ? 'bg-[#F0E6DC] border border-[#C75A3B]/40 text-[#3D3229]'
                            : 'text-[#666555] hover:bg-[#F0E6DC] hover:text-[#3D3229] border border-transparent'
                        }`}
                      >
                        <div className={`p-1.5 rounded-md bg-white border border-[#E8DDD2] mt-0.5 ${item.color}`}>
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-[#3D3229]">{item.label}</span>
                            {isActive && (
                              <span className="text-[9px] uppercase font-bold text-[#2ECC71] flex items-center gap-1 font-mono">
                                <Check className="w-3 h-3" /> Active
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-[#666555] line-clamp-1 mt-0.5">{item.subtitle}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="pt-2 border-t border-[#E8DDD2] flex items-center justify-between text-[11px] px-2 text-[#666555] font-mono">
                  <span>Standalone:</span>
                  <div className="flex items-center gap-2 font-sans font-semibold">
                    <Link href="/monitor" className="text-[#2ECC71] hover:underline flex items-center gap-0.5">
                      Monitor <ExternalLink className="w-2.5 h-2.5" />
                    </Link>
                    <Link href="/arena" className="text-[#C75A3B] hover:underline flex items-center gap-0.5">
                      Arena <ExternalLink className="w-2.5 h-2.5" />
                    </Link>
                    <Link href="/dossier" className="text-[#666555] hover:underline flex items-center gap-0.5">
                      Dossier <ExternalLink className="w-2.5 h-2.5" />
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area Container */}
      {children && <div className="w-full max-w-7xl p-4 md:p-8 flex flex-col items-center">{children}</div>}
    </div>
  );
}
