'use client';

import React, { useState } from 'react';
import { Check, Edit2, Plus, Trash2, ShieldAlert, Sparkles, ArrowRight } from 'lucide-react';

export interface Capability {
  name: string;
  description: string;
  confirmed: boolean;
}

export interface AgentSpecData {
  spec_id: string;
  tenant_id: string;
  agent_name: string;
  raw_description: string;
  domain: string;
  inferred_capabilities: Capability[];
  boundaries: string[];
  risk_domain?: string;
  user_gold_qa?: { question: string; answer: string }[];
  confirmed: boolean;
}

interface Props {
  spec: AgentSpecData;
  onConfirm: (updatedSpec: AgentSpecData) => void;
  loading?: boolean;
}

export default function SpecConfirmationCard({ spec: initialSpec, onConfirm, loading = false }: Props) {
  const [spec, setSpec] = useState<AgentSpecData>(initialSpec);
  const [editingCapIndex, setEditingCapIndex] = useState<number | null>(null);
  const [newCapName, setNewCapName] = useState('');
  const [newCapDesc, setNewCapDesc] = useState('');
  const [newBoundary, setNewBoundary] = useState('');
  const [newQuestion, setNewQuestion] = useState('');
  const [newAnswer, setNewAnswer] = useState('');

  const updateCapability = (index: number, desc: string) => {
    const updated = [...spec.inferred_capabilities];
    updated[index].description = desc;
    setSpec({ ...spec, inferred_capabilities: updated });
    setEditingCapIndex(null);
  };

  const toggleCapability = (index: number) => {
    const updated = [...spec.inferred_capabilities];
    updated[index].confirmed = !updated[index].confirmed;
    setSpec({ ...spec, inferred_capabilities: updated });
  };

  const removeCapability = (index: number) => {
    const updated = spec.inferred_capabilities.filter((_, i) => i !== index);
    setSpec({ ...spec, inferred_capabilities: updated });
  };

  const addCapability = () => {
    if (!newCapName.trim()) return;
    const updated = [
      ...spec.inferred_capabilities,
      { name: newCapName.trim(), description: newCapDesc.trim() || newCapName.trim(), confirmed: true }
    ];
    setSpec({ ...spec, inferred_capabilities: updated });
    setNewCapName('');
    setNewCapDesc('');
  };

  const addBoundary = () => {
    if (!newBoundary.trim()) return;
    setSpec({ ...spec, boundaries: [...spec.boundaries, newBoundary.trim()] });
    setNewBoundary('');
  };

  const removeBoundary = (index: number) => {
    setSpec({ ...spec, boundaries: spec.boundaries.filter((_, i) => i !== index) });
  };

  const addGoldQA = () => {
    if (!newQuestion.trim() || !newAnswer.trim()) return;
    const current = spec.user_gold_qa || [];
    setSpec({
      ...spec,
      user_gold_qa: [...current, { question: newQuestion.trim(), answer: newAnswer.trim() }]
    });
    setNewQuestion('');
    setNewAnswer('');
  };

  return (
    <div className="w-full bg-[#121826] border border-[#232D42] rounded-2xl p-6 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-[#232D42] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Stage 0: Intent Confirmation
            </span>
            {spec.risk_domain && spec.risk_domain !== 'general' && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <ShieldAlert className="w-3 h-3" />
                Risk Domain: {spec.risk_domain}
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-white mt-1.5 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-400" />
            Confirmed Specification for &ldquo;{spec.agent_name}&rdquo;
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review and correct what the machine inferred before generating prompts and running attacks.
          </p>
        </div>
      </div>

      {/* Inferred Capabilities */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Inferred Capabilities ({spec.inferred_capabilities.length})
        </h3>
        <div className="space-y-2">
          {spec.inferred_capabilities.map((cap, idx) => (
            <div
              key={idx}
              className={`p-3.5 rounded-xl border transition-all ${
                cap.confirmed
                  ? 'bg-[#0F1420] border-[#232D42] text-slate-200'
                  : 'bg-slate-900/40 border-slate-800 text-slate-500 line-through'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <button
                    type="button"
                    onClick={() => toggleCapability(idx)}
                    className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center border transition-colors ${
                      cap.confirmed
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'border-slate-700 bg-slate-800 text-transparent'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>

                  <div className="flex-1">
                    <div className="text-sm font-semibold text-white">{cap.name}</div>
                    {editingCapIndex === idx ? (
                      <div className="mt-2 flex gap-2">
                        <input
                          type="text"
                          defaultValue={cap.description}
                          id={`edit-cap-${idx}`}
                          className="flex-1 px-3 py-1.5 text-xs bg-[#0B0F17] border border-blue-500/50 rounded-lg text-white focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const input = document.getElementById(`edit-cap-${idx}`) as HTMLInputElement;
                            updateCapability(idx, input.value);
                          }}
                          className="px-3 py-1 bg-blue-600 text-xs rounded-lg text-white hover:bg-blue-500"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 mt-0.5">{cap.description}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setEditingCapIndex(editingCapIndex === idx ? null : idx)}
                    className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
                    title="Edit capability description"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeCapability(idx)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-500/10"
                    title="Remove capability"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Add new capability inline */}
        <div className="flex gap-2 pt-2">
          <input
            type="text"
            placeholder="Add new capability (e.g. Escalate to supervisor)"
            value={newCapName}
            onChange={(e) => setNewCapName(e.target.value)}
            className="flex-1 px-3 py-2 text-xs bg-[#0B0F17] border border-[#232D42] rounded-lg text-white focus:border-blue-500 focus:outline-none"
          />
          <button
            type="button"
            onClick={addCapability}
            className="px-3 py-2 bg-[#1B2333] hover:bg-[#232D42] border border-[#232D42] text-xs text-slate-200 rounded-lg flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
      </div>

      {/* Explicit Boundaries */}
      <div className="space-y-3 pt-2 border-t border-[#232D42]">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Strict Boundaries & Policy Caps ({spec.boundaries.length})
        </h3>
        <div className="flex flex-wrap gap-2">
          {spec.boundaries.map((b, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs bg-rose-500/10 text-rose-300 border border-rose-500/20"
            >
              <span>{b}</span>
              <button
                type="button"
                onClick={() => removeBoundary(idx)}
                className="hover:text-rose-100"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Add boundary (e.g. Never issue refund above $500)"
            value={newBoundary}
            onChange={(e) => setNewBoundary(e.target.value)}
            className="flex-1 px-3 py-2 text-xs bg-[#0B0F17] border border-[#232D42] rounded-lg text-white focus:border-blue-500 focus:outline-none"
          />
          <button
            type="button"
            onClick={addBoundary}
            className="px-3 py-2 bg-[#1B2333] hover:bg-[#232D42] border border-[#232D42] text-xs text-slate-200 rounded-lg flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> Add Boundary
          </button>
        </div>
      </div>

      {/* Optional User Gold Q&A Set (Circularity Killer) */}
      <div className="space-y-3 pt-2 border-t border-[#232D42]">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            User-Supplied Gold Answers (Weighted Highest in Verify)
          </h3>
          <span className="text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            Non-Circular Truth
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Paste real questions and expected facts from your business. PromptForge scores against your answers, not its own machine guesses.
        </p>

        {spec.user_gold_qa && spec.user_gold_qa.length > 0 && (
          <div className="space-y-2">
            {spec.user_gold_qa.map((qa, i) => (
              <div key={i} className="p-3 bg-[#0F1420] border border-[#232D42] rounded-lg text-xs space-y-1">
                <div className="text-blue-300 font-medium">Q: {qa.question}</div>
                <div className="text-slate-300">A: {qa.answer}</div>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <input
            type="text"
            placeholder="Sample question (e.g. What is the return window?)"
            value={newQuestion}
            onChange={(e) => setNewQuestion(e.target.value)}
            className="px-3 py-2 text-xs bg-[#0B0F17] border border-[#232D42] rounded-lg text-white focus:outline-none focus:border-blue-500"
          />
          <input
            type="text"
            placeholder="Expected answer (e.g. 30 days from purchase date)"
            value={newAnswer}
            onChange={(e) => setNewAnswer(e.target.value)}
            className="px-3 py-2 text-xs bg-[#0B0F17] border border-[#232D42] rounded-lg text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        <button
          type="button"
          onClick={addGoldQA}
          className="px-3 py-1.5 bg-[#1B2333] hover:bg-[#232D42] border border-[#232D42] text-xs text-slate-200 rounded-lg flex items-center gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Add Gold Q&A
        </button>
      </div>

      {/* Footer / Confirm Action */}
      <div className="pt-4 border-t border-[#232D42] flex items-center justify-between">
        <div className="text-xs text-slate-400">
          Status: {spec.confirmed ? 'Confirmed ✓' : 'Awaiting confirmation'}
        </div>
        <button
          type="button"
          onClick={() => onConfirm(spec)}
          disabled={loading}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl flex items-center gap-2 shadow-lg shadow-blue-500/20 transition-all disabled:opacity-50"
        >
          {loading ? 'Confirming...' : 'Confirm & Proceed to Forge'}
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
