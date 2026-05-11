import React, { useState, useRef, useEffect } from 'react';
import { Download, Code, FileJson, Loader2 } from 'lucide-react';
import { exportCode, exportResult } from '../services/api';
import { border_default, text_primary, text_secondary, bg_secondary } from '../styles/design-tokens';

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function ExportButton() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  async function handleExport(type: 'code' | 'result') {
    setOpen(false);
    setError(null);
    setLoading(true);
    try {
      if (type === 'code') {
        const blob = await exportCode();
        triggerDownload(blob, 'via_algorithm.py');
      } else {
        const blob = await exportResult();
        triggerDownload(blob, 'via_result.json');
      }
    } catch {
      setError('Export failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        data-testid="export-button"
        disabled={loading}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded border
                   bg-white/5 backdrop-blur-sm transition-all duration-150
                   hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ borderColor: border_default, color: text_primary }}
      >
        {loading ? (
          <Loader2 size={13} className="animate-spin" data-testid="export-loading" />
        ) : (
          <Download size={13} />
        )}
        Export
      </button>

      {open && (
        <div
          data-testid="export-menu"
          className="absolute right-0 top-full mt-1 min-w-[180px] rounded border
                     bg-white/5 backdrop-blur-sm z-50"
          style={{ borderColor: border_default }}
        >
          <button
            data-testid="export-code-option"
            onClick={() => handleExport('code')}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left
                       hover:bg-white/10 transition-all duration-150"
            style={{ color: text_primary }}
          >
            <Code size={13} style={{ color: text_secondary }} />
            Export Code (.py)
          </button>
          <button
            data-testid="export-result-option"
            onClick={() => handleExport('result')}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left
                       hover:bg-white/10 transition-all duration-150"
            style={{ color: text_primary }}
          >
            <FileJson size={13} style={{ color: text_secondary }} />
            Export Result (.json)
          </button>
        </div>
      )}

      {error && (
        <p
          data-testid="export-error"
          className="absolute right-0 top-full mt-1 text-xs px-3 py-2 rounded border
                     bg-white/5 backdrop-blur-sm whitespace-nowrap"
          style={{ color: '#f87171', borderColor: border_default }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
