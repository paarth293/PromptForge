import React, { ReactNode } from 'react';
import { DEMO_SCENARIOS, DemoScenario } from '../data/demo-scenarios';

export interface DemoModeWrapperProps {
  isEnabled?: boolean;
  currentScenarioId?: string;
  children: ReactNode;
  onScenarioChange?: (scenario: DemoScenario) => void;
}

export function DemoModeWrapper({
  isEnabled = true,
  currentScenarioId = 'demo-jailbreak',
  children,
  onScenarioChange,
}: DemoModeWrapperProps) {
  if (!isEnabled) {
    return <>{children}</>;
  }

  const scenario =
    DEMO_SCENARIOS.find((s) => s.id === currentScenarioId) || DEMO_SCENARIOS[0];

  return (
    <div className="relative">
      {/* Demo Mode Floating Badge */}
      <div className="fixed top-20 right-6 z-40 bg-gradient-to-r from-forge-warning to-forge-orange-rust text-white px-4 py-2 rounded-lg text-xs font-semibold shadow-card-hover flex items-center gap-2 border border-white/20 backdrop-blur-sm">
        <span className="animate-pulse">🎬</span>
        <span>DEMO MODE ACTIVE</span>
        {onScenarioChange && (
          <select
            value={scenario.id}
            onChange={(e) => {
              const found = DEMO_SCENARIOS.find((s) => s.id === e.target.value);
              if (found) onScenarioChange(found);
            }}
            className="ml-2 bg-black/20 text-white text-xs rounded px-1.5 py-0.5 border border-white/30 focus:outline-none"
          >
            {DEMO_SCENARIOS.map((s) => (
              <option key={s.id} value={s.id} className="text-black">
                {s.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Children */}
      {children}
    </div>
  );
}

export default DemoModeWrapper;
