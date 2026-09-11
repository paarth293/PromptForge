'use client';

import React from 'react';
import { Loader2, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';

export interface SmartCardMetadataItem {
  label: string;
  value: string | number;
  highlight?: boolean;
}

export interface SmartCardProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: string;
  badgeVariant?: 'default' | 'success' | 'warning' | 'danger' | 'cost';
  action?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
    variant?: 'primary' | 'secondary' | 'danger';
    disabled?: boolean;
    loading?: boolean;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  status?: 'idle' | 'loading' | 'success' | 'warning' | 'error';
  metadata?: SmartCardMetadataItem[];
  className?: string;
  children: React.ReactNode;
}

export default function SmartCard({
  title,
  subtitle,
  icon,
  badge,
  badgeVariant = 'default',
  action,
  secondaryAction,
  status = 'idle',
  metadata,
  className = '',
  children,
}: SmartCardProps) {
  // Status badges: PASS, FAIL, WARN, COST (Specification Section 4.5)
  const badgeClasses = {
    default: 'bg-[#F0E6DC] text-[#666555] border-[#E8DDD2]',
    success: 'bg-[#2ECC71]/15 text-[#2ECC71] border-[#2ECC71]/30 font-bold',
    warning: 'bg-[#F39C12]/15 text-[#F39C12] border-[#F39C12]/30 font-bold',
    danger: 'bg-[#E74C3C]/15 text-[#E74C3C] border-[#E74C3C]/30 font-bold',
    cost: 'bg-[#C75A3B]/15 text-[#C75A3B] border-[#C75A3B]/30 font-bold',
  }[badgeVariant];

  return (
    <div className={`smart-card w-full p-6 flex flex-col justify-between ${status === 'loading' ? 'loading' : ''} ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#E8DDD2]">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="p-2.5 rounded-xl bg-[#F0E6DC] border border-[#E8DDD2] text-[#C75A3B] shrink-0">
              {icon}
            </div>
          )}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg font-semibold text-[#3D3229] tracking-tight">{title}</h3>
              {badge && (
                <span className={`text-[11px] font-mono uppercase px-2 py-0.5 rounded-md border ${badgeClasses}`}>
                  {badge}
                </span>
              )}
              {status === 'success' && <CheckCircle2 className="w-4 h-4 text-[#2ECC71]" />}
              {status === 'warning' && <AlertTriangle className="w-4 h-4 text-[#F39C12]" />}
              {status === 'error' && <AlertCircle className="w-4 h-4 text-[#E74C3C]" />}
              {status === 'loading' && <Loader2 className="w-4 h-4 text-[#C75A3B] animate-spin" />}
            </div>
            {subtitle && <p className="text-xs text-[#666555] mt-0.5">{subtitle}</p>}
          </div>
        </div>

        {/* Action buttons */}
        {(action || secondaryAction) && (
          <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
            {secondaryAction && (
              <button
                type="button"
                onClick={secondaryAction.onClick}
                className="btn-secondary text-xs"
              >
                {secondaryAction.icon}
                {secondaryAction.label}
              </button>
            )}
            {action && (
              <button
                type="button"
                onClick={action.onClick}
                disabled={action.disabled || action.loading}
                className={`text-xs disabled:opacity-50 ${
                  action.variant === 'danger'
                    ? 'bg-[#E74C3C] hover:bg-[#E74C3C]/90 text-white rounded-lg px-4 py-2 font-semibold shadow-sm'
                    : action.variant === 'secondary'
                    ? 'btn-secondary'
                    : 'btn-primary'
                }`}
              >
                {action.loading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  action.icon
                )}
                {action.label}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Main Card Content */}
      <div className="py-4 flex-1">{children}</div>

      {/* Metadata Footer */}
      {metadata && metadata.length > 0 && (
        <div className="pt-3 border-t border-[#E8DDD2] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-4 flex-wrap">
            {metadata.map((item, idx) => (
              <div key={idx} className="flex items-center gap-1.5 font-mono text-[11px]">
                <span className="text-[#9B8B7E]">{item.label}:</span>
                <span className={`font-semibold ${item.highlight ? 'text-[#C75A3B]' : 'text-[#3D3229]'}`}>
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
