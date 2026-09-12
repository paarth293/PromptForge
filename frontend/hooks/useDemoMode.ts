// Demo Mode Hook for PromptForge Judge Presentation
// Manages switching between BLOCKED, DEGRADED, and COMPROMISED verdict states

import { useState, useEffect } from 'react';
import { DEMO_VERDICTS, DemoVerdictState } from '../fixtures/demo-mode-system';
import { ArenaRunResultData } from '../components/ArenaView';

export interface DemoModeState {
  isEnabled: boolean;
  verdictState: DemoVerdictState;
  verdict: ArenaRunResultData | null;
}

export const useDemoMode = (initialEnabled: boolean = false) => {
  const [isEnabled, setIsEnabled] = useState<boolean>(initialEnabled);
  const [verdictState, setVerdictState] = useState<DemoVerdictState>('blocked');
  const [verdict, setVerdict] = useState<ArenaRunResultData | null>(null);

  // Update verdict whenever verdictState changes
  useEffect(() => {
    if (isEnabled) {
      const selectedVerdict = DEMO_VERDICTS[verdictState];
      setVerdict(selectedVerdict as ArenaRunResultData);
    } else {
      setVerdict(null);
    }
  }, [isEnabled, verdictState]);

  const toggleDemoMode = () => {
    setIsEnabled(!isEnabled);
  };

  const setDemoVerdictState = (state: DemoVerdictState) => {
    setVerdictState(state);
  };

  const getDemoIndicator = () => {
    if (!isEnabled) return null;
    return {
      state: verdictState,
      label: verdictState.charAt(0).toUpperCase() + verdictState.slice(1),
      color: verdictState === 'blocked' ? '#2ECC71' : verdictState === 'degraded' ? '#F39C12' : '#E74C3C',
    };
  };

  return {
    isEnabled,
    verdictState,
    verdict,
    toggleDemoMode,
    setDemoVerdictState,
    getDemoIndicator,
  };
};
