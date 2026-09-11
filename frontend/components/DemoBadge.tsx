'use client';

import React from 'react';

export function DemoBadge({ className = '' }: { className?: string }) {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FBF8F4] border border-[#E8DDD2] text-[11px] font-mono font-semibold text-[#3D3229] shadow-xs ${className}`}
    >
      <span className="w-2 h-2 rounded-full bg-[#2ECC71] animate-pulse" />
      <span className="hidden sm:inline text-[#666555]">ENVIRONMENT:</span>
      <span className="text-[#C75A3B] font-bold">DEMO MODE</span>
    </div>
  );
}

export default DemoBadge;
