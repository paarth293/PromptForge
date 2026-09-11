'use client';

import React, { Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ArrowLeft, FileCheck, ShieldCheck, Cpu } from 'lucide-react';
import DossierView from '../../components/DossierView';

function DossierContent() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get('agentId') || searchParams.get('blueprint_id') || undefined;

  return <DossierView agentId={agentId} />;
}

export default function DossierPage() {
  return (
    <main className="min-h-screen bg-forge-dark text-slate-100 font-sans selection:bg-indigo-600 selection:text-white">
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
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-xs font-medium">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          DOSSIER Passport
        </div>
        <span className="hidden sm:inline text-xs text-slate-500">·</span>
        <span className="hidden sm:inline text-xs text-slate-400">Verifiable Employment Record &amp; Hash-Chain Proof</span>
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
        {/* Dossier Content wrapped in Suspense for useSearchParams */}
        <Suspense
          fallback={
            <div className="p-12 text-center text-slate-400 text-sm">
              <FileCheck className="w-8 h-8 text-indigo-400 animate-pulse mx-auto mb-2" />
              Loading Agent Dossier...
            </div>
          }
        >
          <DossierContent />
        </Suspense>
      </div>
    </main>
  );
}
