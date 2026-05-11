import React from 'react';
import { Terminal, Download, Play, RefreshCw, ExternalLink, AlertTriangle } from 'lucide-react';
import {
  bg_secondary,
  border_default,
  text_primary,
  text_secondary,
  accent_warning,
  accent_error,
} from '../styles/design-tokens';

interface OllamaSetupGuideProps {
  onRetry: () => void;
  onDismiss: () => void;
}

const STEPS = [
  {
    icon: <Download size={14} />,
    label: 'Install Ollama',
    description: (
      <>
        Download and install from{' '}
        <a
          href="https://ollama.ai"
          target="_blank"
          rel="noreferrer"
          className="underline transition-all duration-150 hover:opacity-80"
          style={{ color: text_primary }}
        >
          ollama.ai
        </a>
      </>
    ),
    code: null,
  },
  {
    icon: <Play size={14} />,
    label: 'Start the server',
    description: 'Run this command in a terminal:',
    code: 'ollama serve',
  },
  {
    icon: <Terminal size={14} />,
    label: 'Pull the model',
    description: 'Download the required model:',
    code: 'ollama pull gemma4:e4b',
  },
];

export default function OllamaSetupGuide({ onRetry, onDismiss }: OllamaSetupGuideProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.85)' }}
    >
      <div
        className="w-full max-w-md mx-4 rounded-lg bg-white/5 backdrop-blur-sm border"
        style={{ borderColor: border_default }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-3 px-5 py-4 border-b"
          style={{ borderColor: border_default }}
        >
          <AlertTriangle size={16} style={{ color: accent_warning }} />
          <div>
            <p className="text-sm font-semibold" style={{ color: text_primary }}>
              AI Engine Not Available
            </p>
            <p className="text-xs mt-0.5" style={{ color: text_secondary }}>
              Ollama is required to run local AI inference
            </p>
          </div>
        </div>

        {/* Steps */}
        <div className="px-5 py-4 space-y-4">
          {STEPS.map((step, i) => (
            <div key={i} className="flex gap-3">
              <div
                className="flex items-center justify-center w-6 h-6 rounded-full shrink-0 mt-0.5"
                style={{ backgroundColor: bg_secondary, color: text_secondary }}
              >
                <span className="text-xs font-medium">{i + 1}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span style={{ color: text_secondary }}>{step.icon}</span>
                  <p className="text-sm font-medium" style={{ color: text_primary }}>
                    {step.label}
                  </p>
                </div>
                <p className="text-xs" style={{ color: text_secondary }}>
                  {step.description}
                </p>
                {step.code && (
                  <code
                    className="block mt-1.5 px-3 py-1.5 text-xs rounded font-mono"
                    style={{ backgroundColor: bg_secondary, color: text_primary }}
                  >
                    {step.code}
                  </code>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div
          className="flex items-center justify-between px-5 py-4 border-t"
          style={{ borderColor: border_default }}
        >
          <button
            onClick={onDismiss}
            className="text-xs transition-all duration-150 hover:opacity-80"
            style={{ color: text_secondary }}
          >
            Continue without AI
            <span className="block text-xs" style={{ color: accent_error }}>
              Limited functionality
            </span>
          </button>

          <button
            onClick={onRetry}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 bg-white/5 hover:bg-white/10"
            style={{ borderColor: border_default, color: text_primary }}
          >
            <RefreshCw size={13} />
            Retry Connection
          </button>
        </div>

        {/* Docs link */}
        <div
          className="px-5 pb-4 flex items-center gap-1.5"
        >
          <ExternalLink size={11} style={{ color: text_secondary }} />
          <a
            href="https://ollama.ai/download"
            target="_blank"
            rel="noreferrer"
            className="text-xs underline transition-all duration-150 hover:opacity-80"
            style={{ color: text_secondary }}
          >
            View installation guide
          </a>
        </div>
      </div>
    </div>
  );
}
