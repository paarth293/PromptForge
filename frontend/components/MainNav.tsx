'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Cpu,
  Flame,
  Swords,
  Activity,
  FileCheck,
  Sparkles,
  Shield,
  ShieldCheck,
  ChevronDown,
  Menu,
  X,
  Compass,
  Sliders,
  Play
} from 'lucide-react';

export interface MainNavProps {
  activeStage?: string;
  onNavigateStage?: (stage: any) => void;
  surface?: 'ask' | 'deploy';
  onSurfaceChange?: (surface: 'ask' | 'deploy') => void;
  activeTenant?: string;
  onTenantChange?: (tenantId: string) => void;
  onTriggerDemo?: () => void;
  isDemoRunning?: boolean;
}

export default function MainNav({
  activeStage,
  onNavigateStage,
  surface = 'ask',
  onSurfaceChange,
  activeTenant = 'tenant-demo',
  onTenantChange,
  onTriggerDemo,
  isDemoRunning = false,
}: MainNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [tenantDropdownOpen, setTenantDropdownOpen] = useState(false);

  const navItems = [
    {
      label: 'Forge',
      href: '/',
      id: 'forge',
      icon: Cpu,
      description: 'Agent Synthesis & Policy',
    },
    {
      label: 'Red Team',
      href: '/red-team',
      id: 'redteam',
      icon: Flame,
      description: 'Multi-Turn Attack Studio',
      isStage: true,
      stageId: 'redteam',
    },
    {
      label: 'Arena',
      href: '/arena',
      id: 'arena',
      icon: Swords,
      description: 'Model Sparring Ring',
    },
    {
      label: 'SOC Monitor',
      href: '/monitor',
      id: 'monitor',
      icon: Activity,
      description: 'Fleet Health & Review Queue',
    },
    {
      label: 'Agent Dossier',
      href: '/dossier',
      id: 'dossier',
      icon: FileCheck,
      description: 'Tamper-Proof Audit Passport',
    },
    {
      label: 'Evolve',
      href: '/evolve',
      id: 'evolve',
      icon: Sparkles,
      description: 'Evolutionary Prompt Lineage',
    },
    {
      label: 'Audit',
      href: '/audit',
      id: 'audit',
      icon: Shield,
      description: 'Bring-Your-Own-Agent Zero-Trust Certification',
    },
  ];

  const isActive = (item: typeof navItems[0]) => {
    if (activeStage && activeStage === item.id) {
      return true;
    }
    if (item.href === '/') {
      return pathname === '/' && (!activeStage || activeStage === 'input' || activeStage === 'confirm_spec' || activeStage === 'chat' || activeStage === 'forge');
    }
    if (item.id === 'redteam') {
      return pathname === '/red-team' || (pathname === '/' && activeStage === 'redteam');
    }
    if (item.id === 'audit') {
      return pathname === '/audit' || (pathname === '/' && activeStage === 'audit');
    }
    return pathname.startsWith(item.href);
  };

  const handleNavClick = (item: typeof navItems[0], e: React.MouseEvent) => {
    if (item.id === 'redteam' && pathname === '/' && onNavigateStage) {
      e.preventDefault();
      onNavigateStage('redteam');
      setMobileMenuOpen(false);
    }
  };

  const tenants = ['tenant-demo', 'acme-corp', 'fintech-secure', 'health-core'];

  return (
    <header className="sticky top-0 z-50 w-full h-16 bg-[#F0E6DC] border-b border-[#E8DDD2] shadow-xs px-4 sm:px-6 md:px-8">
      <div className="max-w-7xl mx-auto h-full flex items-center justify-between gap-4">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 group shrink-0">
            <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-[#C75A3B] text-white shadow-md group-hover:bg-[#B84A2F] transition-all transform group-hover:scale-105">
              <Cpu className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight leading-none">
                <span className="text-[#C75A3B]">Prompt</span>
                <span className="text-[#D97D5E]">Forge</span>
              </span>
              <span className="text-[10px] font-semibold text-[#666555] uppercase tracking-wider mt-0.5">
                AI Agent Security
              </span>
            </div>
          </Link>
        </div>

        {/* Center: Desktop Navigation Tabs */}
        <nav className="hidden lg:flex items-center gap-1 xl:gap-2">
          {navItems.map((item) => {
            const active = isActive(item);
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={(e) => handleNavClick(item, e)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  active
                    ? 'bg-[#FBF8F4] text-[#C75A3B] border border-[#E8DDD2] shadow-xs'
                    : 'text-[#666555] hover:text-[#3D3229] hover:bg-[#FBF8F4]/60'
                }`}
                title={item.description}
              >
                <Icon className={`w-3.5 h-3.5 ${active ? 'text-[#C75A3B]' : 'text-[#666555]'}`} />
                <span>{item.label}</span>
                {active && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C75A3B] animate-pulse ml-0.5" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right: Controls & Badges */}
        <div className="flex items-center gap-2.5">
          {/* Quick Demo Trigger Button (Header shortcut) */}
          {onTriggerDemo && (
            <button
              onClick={onTriggerDemo}
              disabled={isDemoRunning}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#C75A3B] hover:bg-[#B84A2F] text-white text-xs font-bold rounded-lg shadow-sm transition-all transform hover:-translate-y-0.5 disabled:opacity-50"
              title="Run 25-Second Hackathon Demonstration"
            >
              <Play className={`w-3.5 h-3.5 fill-current ${isDemoRunning ? 'animate-spin' : ''}`} />
              <span>{isDemoRunning ? 'Demo Running...' : '⚡ Quick Demo'}</span>
            </button>
          )}

          {/* DEMO MODE Badge */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#FBF8F4] border border-[#E8DDD2] text-[11px] font-mono font-semibold text-[#3D3229] shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-[#2ECC71] animate-pulse" />
            <span className="hidden md:inline text-[#666555]">ENVIRONMENT:</span>
            <span className="text-[#C75A3B] font-bold">DEMO MODE</span>
          </div>

          {/* Tenant Selector Dropdown */}
          <div className="relative">
            <button
              onClick={() => setTenantDropdownOpen(!tenantDropdownOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#FBF8F4] border border-[#E8DDD2] text-xs font-medium text-[#3D3229] hover:border-[#C75A3B]/40 transition-colors"
              title="Select Active Tenant"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-[#C75A3B]" />
              <span className="font-mono text-[11px] max-w-[90px] truncate">{activeTenant}</span>
              <ChevronDown className="w-3 h-3 text-[#666555]" />
            </button>

            {tenantDropdownOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl shadow-lg py-1.5 z-50">
                <div className="px-3 py-1 text-[10px] uppercase font-bold text-[#666555] border-b border-[#E8DDD2] mb-1">
                  Tenant Isolation
                </div>
                {tenants.map((t) => (
                  <button
                    key={t}
                    onClick={() => {
                      onTenantChange?.(t);
                      setTenantDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs font-mono transition-colors flex items-center justify-between ${
                      activeTenant === t
                        ? 'bg-[#F0E6DC] text-[#C75A3B] font-bold'
                        : 'text-[#3D3229] hover:bg-[#F0E6DC]/50'
                    }`}
                  >
                    <span>{t}</span>
                    {activeTenant === t && <span className="text-[#C75A3B] font-bold">✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded-lg bg-[#FBF8F4] border border-[#E8DDD2] text-[#3D3229] hover:bg-[#F0E6DC] transition"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4 text-[#C75A3B]" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-16 left-0 w-full bg-[#F0E6DC] border-b border-[#E8DDD2] shadow-xl p-4 space-y-2 z-50">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#666555] px-2 mb-1">
            PromptForge Platform Navigation
          </div>
          <div className="grid grid-cols-2 gap-2">
            {navItems.map((item) => {
              const active = isActive(item);
              const Icon = item.icon;
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={(e) => {
                    handleNavClick(item, e);
                    setMobileMenuOpen(false);
                  }}
                  className={`flex items-center gap-2 p-2.5 rounded-lg text-xs font-medium border transition-all ${
                    active
                      ? 'bg-[#FBF8F4] text-[#C75A3B] border-[#C75A3B]/40 font-bold'
                      : 'bg-[#FBF8F4]/50 text-[#3D3229] border-[#E8DDD2] hover:bg-[#FBF8F4]'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-[#C75A3B]' : 'text-[#666555]'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
