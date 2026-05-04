import React, { useEffect, useRef, useState } from 'react';
import { Play, Square, CheckCircle2, AlertCircle, Cpu, RefreshCw } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { selectExecution } from '../../store/slices/executionSlice';
import {
  setExecutionStatus,
  setExecutionId,
  setCurrentAgent,
  setCurrentIteration,
} from '../../store/slices/executionSlice';
import { startExecution, getExecutionStatus, cancelExecution } from '../../services/api';
import {
  bg_secondary,
  border_default,
  text_primary,
  text_secondary,
  accent_success,
  accent_error,
  accent_warning,
} from '../../styles/design-tokens';

const STATUS_COLORS: Record<string, string> = {
  idle: text_secondary,
  running: accent_warning,
  success: accent_success,
  failed: accent_error,
};

export default function ExecutionPanel() {
  const dispatch = useAppDispatch();
  const execution = useAppSelector(selectExecution);
  const [purposeText, setPurposeText] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Polling
  useEffect(() => {
    if (execution.status !== 'running' || !execution.execution_id) return;

    const id = setInterval(async () => {
      try {
        const res = await getExecutionStatus(execution.execution_id!);
        dispatch(setCurrentAgent(res.current_agent));
        dispatch(setCurrentIteration(res.current_iteration));
        if (res.status !== 'running') {
          dispatch(setExecutionStatus(res.status as any));
          if (res.error) setErrorMessage(res.error);
        }
      } catch {
        // silently ignore transient polling errors
      }
    }, 2000);

    intervalRef.current = id;
    return () => clearInterval(id);
  }, [execution.status, execution.execution_id, dispatch]);

  const handleStart = async () => {
    if (!purposeText.trim()) return;
    try {
      const res = await startExecution(purposeText.trim());
      dispatch(setExecutionId(res.execution_id));
      dispatch(setExecutionStatus('running'));
    } catch (err: any) {
      setErrorMessage(err?.message ?? 'Failed to start execution');
      dispatch(setExecutionStatus('failed'));
    }
  };

  const handleCancel = async () => {
    if (!execution.execution_id) return;
    try {
      await cancelExecution(execution.execution_id);
      dispatch(setExecutionStatus('failed'));
    } catch {
      dispatch(setExecutionStatus('failed'));
    }
  };

  const isRunning = execution.status === 'running';
  const hasStarted = execution.execution_id !== null;

  return (
    <div className="h-full overflow-y-auto p-5 flex flex-col gap-5" style={{ color: text_primary }}>
      {/* Purpose Input */}
      <section>
        <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: text_secondary }}>
          Inspection Purpose
        </label>
        <textarea
          data-testid="purpose-textarea"
          value={purposeText}
          onChange={(e) => setPurposeText(e.target.value)}
          placeholder="Describe the inspection purpose…"
          rows={4}
          className="w-full px-3 py-2 text-sm rounded border bg-white/5 backdrop-blur-sm resize-none transition-all duration-150 focus:outline-none"
          style={{ borderColor: border_default, color: text_primary }}
        />
      </section>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          data-testid="start-btn"
          onClick={handleStart}
          disabled={isRunning || !purposeText.trim()}
          className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 disabled:opacity-40 bg-white/5 backdrop-blur-sm"
          style={{ borderColor: border_default, color: text_primary }}
        >
          {isRunning ? (
            <RefreshCw size={14} className="animate-spin" />
          ) : (
            <Play size={14} />
          )}
          Start
        </button>

        {isRunning && (
          <button
            data-testid="cancel-btn"
            onClick={handleCancel}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 bg-white/5 backdrop-blur-sm"
            style={{ borderColor: accent_error, color: accent_error }}
          >
            <Square size={14} />
            Cancel
          </button>
        )}
      </div>

      {/* Status area */}
      {!hasStarted && (
        <div
          data-testid="idle-state"
          className="flex flex-col items-center justify-center flex-1 gap-2 text-sm"
          style={{ color: text_secondary }}
        >
          <Cpu size={24} strokeWidth={1.5} style={{ color: text_secondary }} />
          <span>No execution started</span>
        </div>
      )}

      {hasStarted && (
        <section
          className="rounded border p-4 bg-white/5 backdrop-blur-sm space-y-3"
          style={{ borderColor: border_default }}
        >
          {/* Status badge */}
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider" style={{ color: text_secondary }}>
              Status
            </span>
            <span
              data-testid="status-badge"
              className="px-2 py-0.5 text-xs rounded font-medium"
              style={{
                color: STATUS_COLORS[execution.status] ?? text_secondary,
                backgroundColor: bg_secondary,
                border: `1px solid ${STATUS_COLORS[execution.status] ?? border_default}`,
              }}
            >
              {execution.status}
            </span>
          </div>

          {/* Current agent */}
          {isRunning && (
            <div className="flex items-center gap-2 text-sm">
              <span style={{ color: text_secondary }}>Agent:</span>
              <span
                data-testid="current-agent"
                className="font-mono text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: bg_secondary, color: text_primary }}
              >
                {execution.current_agent ?? '—'}
              </span>
            </div>
          )}

          {/* Iteration */}
          {isRunning && (
            <div className="flex items-center gap-2 text-sm">
              <span style={{ color: text_secondary }}>Iteration:</span>
              <span
                data-testid="current-iteration"
                className="font-mono text-xs"
                style={{ color: text_primary }}
              >
                {execution.current_iteration}
              </span>
            </div>
          )}

          {/* Success */}
          {execution.status === 'success' && (
            <div
              data-testid="success-message"
              className="flex items-center gap-2 text-sm"
              style={{ color: accent_success }}
            >
              <CheckCircle2 size={14} />
              Execution completed successfully
            </div>
          )}

          {/* Failed */}
          {execution.status === 'failed' && (
            <div
              data-testid="error-message"
              className="flex items-start gap-2 text-sm"
              style={{ color: accent_error }}
            >
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
              <span>{errorMessage || 'Execution failed or was cancelled'}</span>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
