'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Swords, Cpu } from 'lucide-react';
import ArenaView from '../../components/ArenaView';

export default function ArenaPage() {
  return (
    <main className="min-h-screen bg-forge-dark text-slate-100 font-sans selection:bg-red-600 selection:text-white">
      {/* Shared-theme header — matches UnifiedNavigationShell style */}
      <header className="w-full border-b border-forge-border bg-forge-dark/90 backdrop-blur-md sticky top-0 z-50 px-4 md:px-8 py-3 flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2 group shrink-0">
          <div className="w-7 h-7 flex items-center justify-center rounded-lg bg-blue-600/15 text-blue-400 border border-blue-500/25 group-hover:border-blue-400/60 transition-colors">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <span className="text-sm font-bold tracking-tight text-white group-hover:text-blue-200 transition-colors">
            PromptForge
          </span>
        </Link>
        <span className="text-forge-border">/</span>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-red-500/10 border border-red-500/25 text-red-300 text-xs font-medium">
          <Swords className="w-3.5 h-3.5 text-red-400" />
          ARENA Sparring Ring
        </div>
        <span className="hidden sm:inline text-xs text-slate-500">·</span>
        <span className="hidden sm:inline text-xs text-slate-400">Multi-Agent Adversarial &amp; Seam Security</span>
        <div className="flex-1" />
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition group"
        >
          <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
          Back to Forge
        </Link>
      </header>

      <div className="max-w-7xl mx-auto p-4 md:p-8">
        <ArenaView />
      </div>
    </main>
  );
}
