import React, { useState } from 'react';
import { BarChart2, Code2, GitBranch, Trophy } from 'lucide-react';
import { useAppSelector } from '../../store/hooks';
import { selectResult } from '../../store/slices/resultSlice';
import MetricsChart from '../MetricsChart';
import PipelineViewer from '../PipelineViewer';
import {
  bg_secondary,
  border_default,
  text_primary,
  text_secondary,
  accent_info,
  accent_warning,
  accent_error,
  font_mono,
} from '../../styles/design-tokens';

type Tab = 'code' | 'metrics' | 'pipeline' | 'decision';

const DECISION_COLORS: Record<string, string> = {
  RULE_BASED: accent_info,
  EDGE_LEARNING: accent_warning,
  DEEP_LEARNING: accent_error,
};

const KEYWORDS = new Set([
  'import', 'from', 'def', 'return', 'if', 'else', 'elif', 'for', 'while',
  'class', 'in', 'not', 'and', 'or', 'True', 'False', 'None', 'pass', 'break',
  'continue', 'try', 'except', 'finally', 'with', 'as', 'yield', 'lambda',
  'raise', 'del', 'global', 'nonlocal', 'assert', 'async', 'await',
]);

function CodeLine({ line }: { line: string }) {
  // Tokenize: strings → comments → keywords → plain text
  const PATTERN = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(#.*)|(\b[a-zA-Z_]\w*\b)|([\s\S])/g;
  const nodes: React.ReactNode[] = [];
  let match: RegExpExecArray | null;
  let idx = 0;

  while ((match = PATTERN.exec(line)) !== null) {
    if (match[1]) {
      nodes.push(<span key={idx++} style={{ color: '#a3be8c' }}>{match[1]}</span>);
    } else if (match[2]) {
      nodes.push(<span key={idx++} style={{ color: '#6a737d' }}>{match[2]}</span>);
    } else if (match[3]) {
      if (KEYWORDS.has(match[3])) {
        nodes.push(<span key={idx++} style={{ color: '#7ec8e3' }}>{match[3]}</span>);
      } else {
        nodes.push(match[3]);
      }
    } else if (match[4]) {
      nodes.push(match[4]);
    }
  }

  return <>{nodes}</>;
}

export default function ResultPanel() {
  const result = useAppSelector(selectResult);
  const [activeTab, setActiveTab] = useState<Tab>('code');

  if (!result.summary) {
    return (
      <div
        data-testid="empty-state"
        className="flex flex-col items-center justify-center h-full gap-3"
        style={{ color: text_secondary }}
      >
        <BarChart2 size={32} strokeWidth={1.5} />
        <span className="text-sm">실행 결과가 여기에 표시됩니다</span>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'code', label: 'Code', icon: <Code2 size={13} /> },
    { key: 'metrics', label: 'Metrics', icon: <BarChart2 size={13} /> },
    { key: 'pipeline', label: 'Pipeline', icon: <GitBranch size={13} /> },
    { key: 'decision', label: 'Decision', icon: <Trophy size={13} /> },
  ];

  const decisionColor =
    result.decision ? (DECISION_COLORS[result.decision] ?? text_secondary) : text_secondary;

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ color: text_primary }}>
      {/* Summary */}
      <div
        data-testid="summary-text"
        className="px-5 py-3 border-b text-sm font-medium shrink-0 truncate"
        style={{ borderColor: border_default, color: text_primary }}
      >
        {result.summary}
      </div>

      {/* Tab bar */}
      <div
        className="flex gap-1 px-4 py-2 border-b shrink-0"
        style={{ borderColor: border_default }}
      >
        {tabs.map(({ key, label, icon }) => (
          <button
            key={key}
            data-testid={`tab-${key}`}
            onClick={() => setActiveTab(key)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-all duration-150"
            style={{
              color: activeTab === key ? text_primary : text_secondary,
              backgroundColor: activeTab === key ? bg_secondary : 'transparent',
              border: `1px solid ${activeTab === key ? border_default : 'transparent'}`,
            }}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">

        {/* ── Code tab ──────────────────────────────── */}
        {activeTab === 'code' && (
          <div className="flex flex-col gap-4">
            <div
              className="rounded border overflow-hidden"
              style={{ borderColor: border_default, backgroundColor: '#111111' }}
            >
              <div
                className="px-3 py-1.5 text-xs border-b"
                style={{
                  borderColor: border_default,
                  color: text_secondary,
                  backgroundColor: bg_secondary,
                }}
              >
                algorithm.py
              </div>
              <pre
                data-testid="code-block"
                className="overflow-x-auto p-4 text-xs leading-relaxed m-0"
                style={{ fontFamily: font_mono, color: '#e5e5e5' }}
              >
                {result.algorithm_code
                  ? result.algorithm_code.split('\n').map((line, i) => (
                      <div key={i} className="flex">
                        <span
                          className="select-none w-8 shrink-0 text-right pr-3"
                          style={{ color: text_secondary }}
                        >
                          {i + 1}
                        </span>
                        <span>
                          <CodeLine line={line} />
                        </span>
                      </div>
                    ))
                  : <span style={{ color: text_secondary }}>No code available</span>
                }
              </pre>
            </div>

            {result.algorithm_explanation && (
              <div
                data-testid="algorithm-explanation"
                className="p-3 rounded border text-sm leading-relaxed bg-white/5 backdrop-blur-sm"
                style={{ borderColor: border_default, color: text_secondary }}
              >
                {result.algorithm_explanation}
              </div>
            )}
          </div>
        )}

        {/* ── Metrics tab ───────────────────────────── */}
        {activeTab === 'metrics' && (
          <div data-testid="metrics-section" className="flex flex-col gap-4">
            <MetricsChart item_results={result.item_results ?? []} />

            {result.item_results && result.item_results.length > 0 && (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr style={{ color: text_secondary }}>
                    {['Item', 'Pass', 'Accuracy', 'FP Rate', 'FN Rate'].map((h) => (
                      <th
                        key={h}
                        className="text-left py-2 pr-3 border-b font-normal"
                        style={{ borderColor: border_default }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.item_results.map((item: any) => (
                    <tr key={item.item_id}>
                      <td
                        className="py-2 pr-3 font-mono"
                        style={{ color: text_primary }}
                      >
                        {item.item_name}
                      </td>
                      <td
                        className="py-2 pr-3"
                        style={{ color: item.passed ? '#4ade80' : '#f87171' }}
                      >
                        {item.passed ? '✓' : '✗'}
                      </td>
                      <td className="py-2 pr-3" style={{ color: text_secondary }}>
                        {(item.metrics.accuracy * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 pr-3" style={{ color: text_secondary }}>
                        {(item.metrics.fp_rate * 100).toFixed(1)}%
                      </td>
                      <td className="py-2" style={{ color: text_secondary }}>
                        {(item.metrics.fn_rate * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ── Pipeline tab ──────────────────────────── */}
        {activeTab === 'pipeline' && (
          <div data-testid="pipeline-section">
            <PipelineViewer pipeline={result.pipeline} />
          </div>
        )}

        {/* ── Decision tab ──────────────────────────── */}
        {activeTab === 'decision' && (
          <div data-testid="decision-section" className="flex flex-col gap-5">
            {result.decision && (
              <div className="flex flex-col gap-3">
                <span
                  data-testid="decision-badge"
                  className="self-start px-3 py-1.5 text-sm font-semibold rounded"
                  style={{
                    color: decisionColor,
                    backgroundColor: `${decisionColor}20`,
                    border: `1px solid ${decisionColor}60`,
                  }}
                >
                  {result.decision}
                </span>

                {result.decision_reason && (
                  <p
                    data-testid="decision-reason"
                    className="text-sm leading-relaxed"
                    style={{ color: text_secondary }}
                  >
                    {result.decision_reason}
                  </p>
                )}
              </div>
            )}

            {result.improvement_suggestions && result.improvement_suggestions.length > 0 && (
              <div className="flex flex-col gap-2">
                <h4
                  className="text-xs font-medium uppercase tracking-wider"
                  style={{ color: text_secondary }}
                >
                  Improvement Suggestions
                </h4>
                <ul data-testid="suggestions-list" className="flex flex-col gap-1.5">
                  {result.improvement_suggestions.map((s: string, i: number) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm p-2.5 rounded border bg-white/5 backdrop-blur-sm transition-all duration-150"
                      style={{ borderColor: border_default, color: text_secondary }}
                    >
                      <span
                        className="shrink-0 mt-0.5"
                        style={{ color: accent_warning }}
                      >
                        →
                      </span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
