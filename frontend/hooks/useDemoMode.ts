import { useEffect, useState, useCallback, useRef } from 'react';
import { DemoScenario, DemoStep } from '../data/demo-scenarios';

export interface UseDemoModeReturn {
  currentStepIndex: number;
  currentStep: DemoStep | null;
  progress: number;
  costTicker: number;
  isPlaying: boolean;
  startDemo: () => void;
  stopDemo: () => void;
  resetDemo: () => void;
}

export function useDemoMode(scenario: DemoScenario): UseDemoModeReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [progress, setProgress] = useState(0);
  const [costTicker, setCostTicker] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);
  const animRef = useRef<number | null>(null);

  // Main animation loop
  useEffect(() => {
    if (!isPlaying || !startTime) return;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const percentComplete = Math.min((elapsed / scenario.duration) * 100, 100);

      // Update overall progress
      setProgress(percentComplete);

      // Update which step is active
      let activeStepIdx = -1;
      for (let i = 0; i < scenario.steps.length; i++) {
        if (elapsed >= scenario.steps[i].startTime) {
          activeStepIdx = i;
        }
      }
      setCurrentStepIndex(activeStepIdx);

      // Animate cost ticker
      const targetCost = scenario.costBreakdown.total;
      const currentCostProgress = percentComplete / 100;
      setCostTicker(+(targetCost * currentCostProgress).toFixed(4));

      // Continue animation or stop
      if (elapsed >= scenario.duration) {
        setIsPlaying(false);
        setProgress(100);
        setCostTicker(targetCost);
        setCurrentStepIndex(scenario.steps.length);
      } else {
        animRef.current = requestAnimationFrame(animate);
      }
    };

    animRef.current = requestAnimationFrame(animate);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isPlaying, startTime, scenario]);

  const startDemo = useCallback(() => {
    setStartTime(Date.now());
    setIsPlaying(true);
    setCurrentStepIndex(0);
    setProgress(0);
    setCostTicker(0);
  }, []);

  const stopDemo = useCallback(() => {
    setIsPlaying(false);
    if (animRef.current) cancelAnimationFrame(animRef.current);
  }, []);

  const resetDemo = useCallback(() => {
    setIsPlaying(false);
    if (animRef.current) cancelAnimationFrame(animRef.current);
    setCurrentStepIndex(-1);
    setProgress(0);
    setCostTicker(0);
    setStartTime(null);
  }, []);

  const currentStep =
    currentStepIndex >= 0 && currentStepIndex < scenario.steps.length
      ? scenario.steps[currentStepIndex]
      : null;

  return {
    currentStepIndex,
    currentStep,
    progress,
    costTicker,
    isPlaying,
    startDemo,
    stopDemo,
    resetDemo,
  };
}

export default useDemoMode;
