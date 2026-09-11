'use client';

import { useState, useRef, useCallback } from 'react';
import demoData from '../data/demo-scenarios.json';

export interface DemoAttackItem {
  id: string;
  name: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  status: 'UNSAFE' | 'WARN' | 'SAFE';
  confidence: number;
  layer: string;
  attack_prompt: string;
  findings: string;
  cost: number;
  recommendation: string;
}

export function useHackathonDemo() {
  const scenario = demoData.scenario_1;
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoCompleted, setDemoCompleted] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0 = idle, 1=Persona, 2=Crafting, 3=Execution, 4=Judge
  const [currentCost, setCurrentCost] = useState(0);
  const [visibleAttacks, setVisibleAttacks] = useState<DemoAttackItem[]>([]);
  const [robustnessScore, setRobustnessScore] = useState(42);
  const [attackSuccessRate, setAttackSuccessRate] = useState(58);
  const [activeTab, setActiveTab] = useState<'cascade' | 'vulnerabilities' | 'cost' | 'diff'>('cascade');

  const timeoutRefs = useRef<NodeJS.Timeout[]>([]);

  const clearTimeouts = () => {
    timeoutRefs.current.forEach((t) => clearTimeout(t));
    timeoutRefs.current = [];
  };

  const fastForwardDemo = useCallback(() => {
    clearTimeouts();
    setCurrentStep(4);
    setCurrentCost(scenario.costSummary.total);
    setVisibleAttacks(scenario.attacks as DemoAttackItem[]);
    setRobustnessScore(scenario.metricsAfter.robustness);
    setAttackSuccessRate(scenario.metricsAfter.attackSuccessRate);
    setIsDemoRunning(false);
    setDemoCompleted(true);
  }, [scenario]);

  const runDemo = useCallback(() => {
    clearTimeouts();
    setIsDemoRunning(true);
    setDemoCompleted(false);
    setCurrentStep(1);
    setCurrentCost(0.05);
    setVisibleAttacks([]);
    setRobustnessScore(42);
    setAttackSuccessRate(58);
    setActiveTab('cascade');

    // Sequence schedule (total ~4-5 seconds for snappy hackathon demo without boring the judge)
    // Step 1: Persona Loading
    const t1 = setTimeout(() => {
      setCurrentStep(1);
      setCurrentCost(0.18);
    }, 400);

    // Step 2: Attack Crafting
    const t2 = setTimeout(() => {
      setCurrentStep(2);
      setCurrentCost(0.64);
      // reveal first 2 attacks
      setVisibleAttacks(scenario.attacks.slice(0, 2) as DemoAttackItem[]);
    }, 1000);

    // Step 3: Sandboxed Execution
    const t3 = setTimeout(() => {
      setCurrentStep(3);
      setCurrentCost(1.45);
      // reveal next 3 attacks
      setVisibleAttacks(scenario.attacks.slice(0, 5) as DemoAttackItem[]);
    }, 1800);

    // Step 4: Judge Evaluation & final metrics
    const t4 = setTimeout(() => {
      setCurrentStep(4);
      setCurrentCost(2.34);
      setVisibleAttacks(scenario.attacks as DemoAttackItem[]);
    }, 2700);

    // Final completion & hardening metrics update
    const t5 = setTimeout(() => {
      setIsDemoRunning(false);
      setDemoCompleted(true);
      setRobustnessScore(96);
      setAttackSuccessRate(4);
    }, 3400);

    timeoutRefs.current.push(t1, t2, t3, t4, t5);
  }, [scenario]);

  const resetDemo = useCallback(() => {
    clearTimeouts();
    setIsDemoRunning(false);
    setDemoCompleted(false);
    setCurrentStep(0);
    setCurrentCost(0);
    setVisibleAttacks([]);
    setRobustnessScore(42);
    setAttackSuccessRate(58);
    setActiveTab('cascade');
  }, []);

  return {
    scenario,
    isDemoRunning,
    demoCompleted,
    currentStep,
    currentCost,
    visibleAttacks,
    robustnessScore,
    attackSuccessRate,
    activeTab,
    setActiveTab,
    runDemo,
    fastForwardDemo,
    resetDemo,
  };
}
