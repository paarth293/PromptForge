'use client';

import React, { Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ArrowLeft, FileCheck, ShieldCheck } from 'lucide-react';
import DossierView from '../../components/DossierView';

function DossierContent() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get('agentId') || searchParams.get('blueprint_id') || undefined;

  return <DossierView agentId={agentId} />;
}

export default function DossierPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans selection:bg-indigo-600 selection:text-white">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Navigation Bar */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <Link
            href="/"
            className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white transition group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            <span>Return to PromptForge Home</span>
          </Link>
          <div className="flex items-center space-x-3 text-xs text-slate-400">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-950/60 border border-indigo-800/40 text-indigo-300">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              <span>Verifiable Employment Record</span>
            </span>
            <span className="text-slate-600">•</span>
            <span>Birth Certificate Hash Chain Proof</span>
          </div>
        </div>

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
