'use client';

import React, { useState } from 'react';
import { Button } from './Button';
import { FileDown, CheckCircle2, AlertCircle } from 'lucide-react';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

export interface ExportButtonProps {
  campaignId: string;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

export function ExportButton({
  campaignId,
  variant = 'secondary',
  size = 'md',
  label = 'Export PDF Report',
  className = '',
}: ExportButtonProps) {
  const [downloading, setDownloading] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleExport = async () => {
    if (downloading) return;
    setDownloading(true);
    setDownloadError(null);
    setDownloadSuccess(false);

    try {
      const response = await fetch(`${API_BASE_URL}/api/export/campaign/${encodeURIComponent(campaignId)}/pdf`, {
        method: 'GET',
        headers: {
          'X-Tenant-ID': 'tenant-demo',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to generate PDF (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `promptforge-report-${campaignId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 3000);
    } catch (err: any) {
      console.error('PDF export error:', err);
      setDownloadError(err?.message || 'Download failed');
      setTimeout(() => setDownloadError(null), 4000);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="inline-flex items-center gap-2">
      <Button
        onClick={handleExport}
        isLoading={downloading}
        variant={downloadSuccess ? 'secondary' : variant}
        size={size}
        className={className}
        title="Download executive audit & red team PDF report"
      >
        {downloadSuccess ? (
          <>
            <CheckCircle2 className="w-4 h-4 text-forge-success" />
            <span>Downloaded!</span>
          </>
        ) : (
          <>
            <FileDown className="w-4 h-4 text-forge-orange-rust" />
            <span>{label}</span>
          </>
        )}
      </Button>

      {downloadError && (
        <span className="text-xs text-forge-critical flex items-center gap-1 font-medium animate-fade-in">
          <AlertCircle className="w-3.5 h-3.5" />
          {downloadError}
        </span>
      )}
    </div>
  );
}

export default ExportButton;
