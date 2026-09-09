'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Swords } from 'lucide-react';
import ArenaView from '../../components/ArenaView';

export default function ArenaPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans selection:bg-red-600 selection:text-white">
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
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/60 border border-red-800/40 text-red-300">
              <Swords className="w-3.5 h-3.5 text-red-400" />
              <span>ARENA Sparring Ring</span>
            </span>
            <span className="text-slate-600">•</span>
            <span>Multi-Agent Adversarial & Seam Security</span>
          </div>
        </div>

        {/* Arena View Component */}
        <ArenaView />
      </div>
    </main>
  );
}
