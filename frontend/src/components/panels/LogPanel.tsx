import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, ScrollText, Trash2 } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { selectExecution } from '../../store/slices/executionSlice';
import { clearLogs as clearLogsAction } from '../../store/slices/logsSlice';
import {
  getLogs,
  getLogAgents,
  clearLogs as clearLogsAPI,
} from '../../services/api';
import type { LogEntry } from '../../services/types';
import {
  bg_secondary,
  border_default,
  text_primary,
  text_secondary,
  accent_error,
} from '../../styles/design-tokens';

const AGENT_COLOR_PALETTE = [
  '#e2e8f0',
  '#f9a8d4',
  '#a78bfa',
  '#67e8f9',
  '#86efac',
  '#fde68a',
  '#fdba74',
  '#c4b5fd',
  '#6ee7b7',
  '#fca5a5',
  '#93c5fd',
  '#d9f99d',
];

function getAgentColor(agentName: string): string {
  let hash = 0;
  for (let i = 0; i < agentName.length; i++) {
    hash = (hash * 31 + agentName.charCodeAt(i)) & 0x7fffffff;
  }
  return AGENT_COLOR_PALETTE[hash % AGENT_COLOR_PALETTE.length];
}

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: '#a0a0a0',
  INFO: '#60a5fa',
  WARNING: '#facc15',
  ERROR: '#f87171',
};

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    const ms = String(d.getMilliseconds()).padStart(3, '0');
    return `${hh}:${mm}:${ss}.${ms}`;
  } catch {
    return ts;
  }
}

export default function LogPanel() {
  const dispatch = useAppDispatch();
  const execution = useAppSelector(selectExecution);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agents, setAgents] = useState<string[]>([]);
  const [agentFilter, setAgentFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState('');

  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async (agent?: string, level?: string) => {
    try {
      const params: { agent?: string; level?: string } = {};
      if (agent) params.agent = agent;
      if (level) params.level = level;
      const res = await getLogs(Object.keys(params).length ? params : undefined);
      setLogs(res.logs);
      setError(null);
    } catch {
      setError('Failed to load logs');
    }
  };

  useEffect(() => {
    Promise.all([
      fetchLogs(),
      getLogAgents()
        .then((r) => setAgents(r.agents ?? []))
        .catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  useEffect(() => {
    if (execution.status !== 'running') return;
    const id = setInterval(() => {
      fetchLogs(agentFilter || undefined, levelFilter || undefined);
    }, 2000);
    return () => clearInterval(id);
  }, [execution.status, agentFilter, levelFilter]);

  const handleAgentFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setAgentFilter(val);
    fetchLogs(val || undefined, levelFilter || undefined);
  };

  const handleLevelFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setLevelFilter(val);
    fetchLogs(agentFilter || undefined, val || undefined);
  };

  const handleRefresh = () => {
    fetchLogs(agentFilter || undefined, levelFilter || undefined);
  };

  const handleClear = async () => {
    try {
      await clearLogsAPI();
      dispatch(clearLogsAction());
      setLogs([]);
    } catch {
      // silently ignore
    }
  };

  return (
    <div className="h-full flex flex-col p-5 gap-4" style={{ color: text_primary }}>
      {/* Header toolbar */}
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        <span className="text-xs uppercase tracking-wider mr-1" style={{ color: text_secondary }}>
          Logs
        </span>
        <span
          data-testid="log-count"
          className="px-2 py-0.5 text-xs rounded font-mono"
          style={{ backgroundColor: bg_secondary, color: text_secondary }}
        >
          {logs.length}
        </span>

        <div className="flex-1" />

        <select
          data-testid="agent-filter"
          value={agentFilter}
          onChange={handleAgentFilterChange}
          className="px-2 py-1 text-xs rounded border bg-white/5 backdrop-blur-sm transition-all duration-150 focus:outline-none"
          style={{ borderColor: border_default, color: text_secondary, backgroundColor: '#111111' }}
        >
          <option value="">All Agents</option>
          {(agents ?? []).map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>

        <select
          data-testid="level-filter"
          value={levelFilter}
          onChange={handleLevelFilterChange}
          className="px-2 py-1 text-xs rounded border bg-white/5 backdrop-blur-sm transition-all duration-150 focus:outline-none"
          style={{ borderColor: border_default, color: text_secondary, backgroundColor: '#111111' }}
        >
          <option value="">All Levels</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>

        <button
          data-testid="refresh-btn"
          onClick={handleRefresh}
          className="p-1.5 rounded border bg-white/5 backdrop-blur-sm transition-all duration-150"
          style={{ borderColor: border_default, color: text_secondary }}
        >
          <RefreshCw size={13} />
        </button>

        <button
          data-testid="clear-btn"
          onClick={handleClear}
          className="p-1.5 rounded border bg-white/5 backdrop-blur-sm transition-all duration-150"
          style={{ borderColor: border_default, color: text_secondary }}
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Body */}
      {loading && (
        <div
          data-testid="logs-loading"
          className="flex-1 flex items-center justify-center gap-2 text-sm"
          style={{ color: text_secondary }}
        >
          <RefreshCw size={16} className="animate-spin" />
          Loading…
        </div>
      )}

      {!loading && error && (
        <div
          data-testid="logs-error"
          className="flex-1 flex items-center justify-center text-sm"
          style={{ color: accent_error }}
        >
          {error}
        </div>
      )}

      {!loading && !error && logs.length === 0 && (
        <div
          data-testid="empty-state"
          className="flex-1 flex flex-col items-center justify-center gap-2 text-sm"
          style={{ color: text_secondary }}
        >
          <ScrollText size={24} strokeWidth={1.5} />
          No logs yet. Start an execution to see agent logs.
        </div>
      )}

      {!loading && !error && logs.length > 0 && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto"
          style={{ maxHeight: '100%' }}
        >
          {logs.map((log, i) => (
            <div
              key={i}
              data-testid={`log-entry-${i}`}
              className="flex items-start gap-2 px-2 py-1 rounded text-xs font-mono hover:bg-white/5 transition-all duration-150"
            >
              <span className="shrink-0 tabular-nums" style={{ color: text_secondary }}>
                {formatTimestamp(log.timestamp)}
              </span>
              <span
                data-testid={`agent-badge-${i}`}
                className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold"
                style={{
                  color: getAgentColor(log.agent),
                  backgroundColor: bg_secondary,
                }}
              >
                {log.agent}
              </span>
              <span
                data-testid={`level-badge-${i}`}
                className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase"
                style={{
                  color: LEVEL_COLORS[log.level] ?? text_secondary,
                  backgroundColor: bg_secondary,
                }}
              >
                {log.level}
              </span>
              <span className="flex-1 break-all" style={{ color: text_primary }}>
                {log.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
