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
    <div className="w-full bg-[#FBF8F4] border border-[#E8DDD2] rounded-xl p-6 shadow-card space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-[#E8DDD2] pb-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F0E6DC] text-[#C75A3B] border border-[#E8DDD2]">
              Stage 2: Intent &amp; Boundary Confirmation
            </span>
            {spec.risk_domain && spec.risk_domain !== 'general' && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F39C12]/15 text-[#F39C12] border border-[#F39C12]/30 flex items-center gap-1">
                <ShieldAlert className="w-3 h-3" />
                Risk Domain: {spec.risk_domain}
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-[#3D3229] mt-2 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#C75A3B]" />
            Confirmed Specification for &ldquo;{spec.agent_name}&rdquo;
          </h2>
          <p className="text-xs text-[#666555] mt-1">
            Review and adjust inferred capabilities and boundaries before generating CRISPE prompts and initiating attacks.
          </p>
        </div>
      </div>

      {/* Inferred Capabilities */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-[#3D3229]">
          Inferred Capabilities ({spec.inferred_capabilities.length})
        </h3>
        <div className="space-y-2">
          {spec.inferred_capabilities.map((cap, idx) => (
            <div
              key={idx}
              className={`p-3.5 rounded-xl border transition-all ${
                cap.confirmed
                  ? 'bg-white border-[#E8DDD2] text-[#3D3229] shadow-xs'
                  : 'bg-[#F0E6DC]/40 border-[#E8DDD2] text-[#9B8B7E] line-through'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <button
                    type="button"
                    onClick={() => toggleCapability(idx)}
                    className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center border transition-colors ${
                      cap.confirmed
                        ? 'bg-[#C75A3B] border-[#C75A3B] text-white'
                        : 'border-[#E8DDD2] bg-white text-transparent'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>

                  <div className="flex-1">
                    <div className="text-sm font-semibold text-[#3D3229]">{cap.name}</div>
                    {editingCapIndex === idx ? (
                      <div className="mt-2 flex gap-2">
                        <input
                          type="text"
                          defaultValue={cap.description}
                          id={`edit-cap-${idx}`}
                          className="flex-1 px-3 py-1.5 text-xs bg-white border border-[#C75A3B] rounded-lg text-[#3D3229] focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const input = document.getElementById(`edit-cap-${idx}`) as HTMLInputElement;
                            updateCapability(idx, input.value);
                          }}
                          className="btn-primary text-xs py-1 px-3"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <p className="text-xs text-[#666555] mt-0.5">{cap.description}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setEditingCapIndex(editingCapIndex === idx ? null : idx)}
                    className="p-1.5 text-[#666555] hover:text-[#3D3229] rounded-lg hover:bg-[#F0E6DC]"
                    title="Edit capability description"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeCapability(idx)}
                    className="p-1.5 text-[#666555] hover:text-[#E74C3C] rounded-lg hover:bg-[#E74C3C]/10"
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
            className="flex-1 px-3.5 py-2 text-xs bg-white border border-[#E8DDD2] rounded-lg text-[#3D3229] placeholder-[#9B8B7E] focus:border-[#C75A3B] focus:outline-none"
          />
          <button
            type="button"
            onClick={addCapability}
            className="btn-secondary text-xs"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
      </div>

      {/* Explicit Boundaries */}
      <div className="space-y-3 pt-2 border-t border-[#E8DDD2]">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-[#3D3229]">
          Strict Boundaries &amp; Policy Caps ({spec.boundaries.length})
        </h3>
        <div className="flex flex-wrap gap-2">
          {spec.boundaries.map((b, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs bg-[#E74C3C]/10 text-[#E74C3C] border border-[#E74C3C]/20 font-medium"
            >
              <span>{b}</span>
              <button
                type="button"
                onClick={() => removeBoundary(idx)}
                className="hover:opacity-75 font-bold"
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
            className="flex-1 px-3.5 py-2 text-xs bg-white border border-[#E8DDD2] rounded-lg text-[#3D3229] placeholder-[#9B8B7E] focus:border-[#C75A3B] focus:outline-none"
          />
          <button
            type="button"
            onClick={addBoundary}
            className="btn-secondary text-xs"
          >
            <Plus className="w-3.5 h-3.5" /> Add Boundary
          </button>
        </div>
      </div>

      {/* Optional User Gold Q&A Set (Circularity Killer) */}
      <div className="space-y-3 pt-2 border-t border-[#E8DDD2]">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-[#3D3229]">
            User-Supplied Gold Answers (Weighted Highest in Verify)
          </h3>
          <span className="text-[11px] text-[#2ECC71] bg-[#2ECC71]/10 px-2 py-0.5 rounded border border-[#2ECC71]/20 font-bold">
            Non-Circular Truth
          </span>
        </div>
        <p className="text-xs text-[#666555]">
          Paste real questions and expected facts from your domain. PromptForge verifies against your answers, not circular LLM hallucinations.
        </p>

        {spec.user_gold_qa && spec.user_gold_qa.length > 0 && (
          <div className="space-y-2">
            {spec.user_gold_qa.map((qa, i) => (
              <div key={i} className="p-3 bg-white border border-[#E8DDD2] rounded-lg text-xs space-y-1 shadow-xs">
                <div className="text-[#C75A3B] font-semibold">Q: {qa.question}</div>
                <div className="text-[#3D3229]">A: {qa.answer}</div>
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
            className="px-3.5 py-2 text-xs bg-white border border-[#E8DDD2] rounded-lg text-[#3D3229] placeholder-[#9B8B7E] focus:outline-none focus:border-[#C75A3B]"
          />
          <input
            type="text"
            placeholder="Expected answer (e.g. 30 days from purchase date)"
            value={newAnswer}
            onChange={(e) => setNewAnswer(e.target.value)}
            className="px-3.5 py-2 text-xs bg-white border border-[#E8DDD2] rounded-lg text-[#3D3229] placeholder-[#9B8B7E] focus:outline-none focus:border-[#C75A3B]"
          />
        </div>
        <button
          type="button"
          onClick={addGoldQA}
          className="btn-secondary text-xs self-start"
        >
          <Plus className="w-3.5 h-3.5" /> Add Gold Q&amp;A
        </button>
      </div>

      {/* Footer / Confirm Action */}
      <div className="pt-4 border-t border-[#E8DDD2] flex items-center justify-between">
        <div className="text-xs text-[#666555]">
          Status: <strong className="text-[#3D3229]">{spec.confirmed ? 'Confirmed ✓' : 'Awaiting confirmation'}</strong>
        </div>
        <button
          type="button"
          onClick={() => onConfirm(spec)}
          disabled={loading}
          className="btn-primary text-xs"
        >
          {loading ? 'Confirming...' : 'Confirm & Proceed to Forge'}
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
