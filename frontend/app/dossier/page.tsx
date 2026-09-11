'use client';

import React, { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { FileCheck } from 'lucide-react';
import MainNav from '../../components/MainNav';
import DossierView from '../../components/DossierView';

function DossierContent() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get('agentId') || searchParams.get('blueprint_id') || undefined;

  return <DossierView agentId={agentId} />;
}

export default function DossierPage() {
  return (
    <main className="min-h-screen bg-[#F9F5F0] text-[#3D3229] font-sans selection:bg-[#C75A3B] selection:text-white">
      {/* Global Unified Navigation Bar (Action 1 & 4) */}
      <MainNav activeStage="dossier" />

      <div className="max-w-7xl mx-auto p-4 md:p-8">
        {/* Dossier Content wrapped in Suspense for useSearchParams */}
        <Suspense
          fallback={
            <div className="p-12 text-center text-[#666555] text-sm bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl">
              <FileCheck className="w-8 h-8 text-[#C75A3B] animate-pulse mx-auto mb-2" />
              Loading Agent Dossier Passport...
            </div>
          }
        >
          <DossierContent />
        </Suspense>
      </div>
    </main>
  );
}
