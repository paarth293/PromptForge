'use client';

import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export type MessageType = 'success' | 'error' | 'warning' | 'info';

export interface MessageBannerProps {
  type: MessageType;
  title?: string;
  message: string;
  onClose?: () => void;
  className?: string;
}

export function MessageBanner({
  type,
  title,
  message,
  onClose,
  className = '',
}: MessageBannerProps) {
  const styles = {
    success: {
      bg: 'bg-[#2ECC71]/10',
      border: 'border-[#2ECC71]/30',
      text: 'text-[#2ECC71]',
      titleColor: 'text-[#2ECC71]',
      icon: CheckCircle2,
    },
    error: {
      bg: 'bg-[#E74C3C]/10',
      border: 'border-[#E74C3C]/30',
      text: 'text-[#E74C3C]',
      titleColor: 'text-[#E74C3C]',
      icon: AlertCircle,
    },
    warning: {
      bg: 'bg-[#F39C12]/10',
      border: 'border-[#F39C12]/30',
      text: 'text-[#F39C12]',
      titleColor: 'text-[#F39C12]',
      icon: AlertTriangle,
    },
    info: {
      bg: 'bg-[#C75A3B]/10',
      border: 'border-[#C75A3B]/30',
      text: 'text-[#C75A3B]',
      titleColor: 'text-[#C75A3B]',
      icon: Info,
    },
  }[type];

  const Icon = styles.icon;

  return (
    <div
      className={`rounded-xl border p-4 flex items-start justify-between gap-3 shadow-card animate-in fade-in duration-200 ${styles.bg} ${styles.border} ${className}`}
    >
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${styles.text}`} />
        <div className="space-y-0.5">
          {title && (
            <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.titleColor}`}>
              {title}
            </h4>
          )}
          <p className="text-xs text-[#3D3229] leading-relaxed break-words">{message}</p>
        </div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-[#666555] hover:text-[#3D3229] hover:bg-black/5 transition-colors"
          title="Dismiss message"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default MessageBanner;
