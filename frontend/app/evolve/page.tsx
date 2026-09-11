'use client';

import React from 'react';
import MainNav from '../../components/MainNav';
import DeepForgeLineageViewer from '../../components/DeepForgeLineageViewer';

export default function EvolvePage() {
  return (
    <main className="min-h-screen bg-[#F9F5F0] text-[#3D3229] font-sans selection:bg-[#C75A3B] selection:text-white">
      {/* Global Unified Navigation Bar (Action 1 & 4) */}
      <MainNav activeStage="evolve" />

      <div className="max-w-7xl mx-auto p-4 md:p-8">
        <DeepForgeLineageViewer />
      </div>
    </main>
  );
}
