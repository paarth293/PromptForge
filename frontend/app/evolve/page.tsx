'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Dna, ShieldAlert, Sparkles } from 'lucide-react';
import DeepForgeLineageViewer from '../../components/DeepForgeLineageViewer';

export default function EvolvePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans selection:bg-purple-600 selection:text-white">
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
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-purple-950/60 border border-purple-800/40 text-purple-300">
              <Dna className="w-3.5 h-3.5 text-purple-400" />
              <span>Deep Forge Engine</span>
            </span>
            <span className="text-slate-600">•</span>
            <span>Evolutionary Multi-Generation Mode</span>
          </div>
        </div>

        {/* Lineage Viewer */}
        <DeepForgeLineageViewer />
      </div>
    </main>
  );
}
