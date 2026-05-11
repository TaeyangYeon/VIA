import React, { useEffect, useState } from 'react';
import { Save, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import {
  selectConfig,
  setMode,
  setMaxIteration,
  setSuccessCriteria,
} from '../../store/slices/configSlice';
import { saveConfig, getConfig } from '../../services/api';
import {
  bg_secondary,
  border_default,
  border_emphasis,
  text_primary,
  text_secondary,
  accent_success,
  accent_error,
  accent_warning,
} from '../../styles/design-tokens';

type SaveState = 'idle' | 'loading' | 'success' | 'error';

export default function ConfigPanel() {
  const dispatch = useAppDispatch();
  const config = useAppSelector(selectConfig);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [saveError, setSaveError] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);

  useEffect(() => {
    getConfig()
      .then((cfg) => {
        dispatch(setMode(cfg.mode));
        dispatch(setMaxIteration(cfg.max_iteration));
        dispatch(setSuccessCriteria(cfg.success_criteria));
      })
      .catch((err) => {
        if (err?.response?.status !== 404) {
          // non-404 errors are silently ignored; defaults remain
        }
      });
  }, [dispatch]);

  const handleModeChange = (newMode: 'inspection' | 'align') => {
    dispatch(setMode(newMode));
    if (newMode === 'inspection') {
      dispatch(setSuccessCriteria({ accuracy: 0.95, fp_rate: 0.05, fn_rate: 0.05 }));
    } else {
      dispatch(setSuccessCriteria({ coord_error: 2.0, success_rate: 0.9 }));
    }
  };

  const handleMaxIterationChange = (val: string) => {
    const n = parseInt(val, 10);
    if (!isNaN(n) && n >= 1 && n <= 20) {
      dispatch(setMaxIteration(n));
    }
  };

  const handleCriteriaChange = (field: string, val: string) => {
    const n = parseFloat(val);
    if (isNaN(n)) return;
    dispatch(setSuccessCriteria({ ...(config.success_criteria as any), [field]: n }));
  };

  const handleSave = async () => {
    setSaveState('loading');
    setSaveError('');
    setWarnings([]);
    try {
      const res = await saveConfig(config);
      setWarnings(res.warnings ?? []);
      setSaveState('success');
    } catch (err: any) {
      setSaveError(err?.message ?? 'Save failed');
      setSaveState('error');
    }
  };

  const criteria = config.success_criteria as any;

  const modeButtonStyle = (active: boolean) => ({
    borderColor: active ? text_primary : border_default,
    color: active ? text_primary : text_secondary,
    backgroundColor: active ? bg_secondary : 'transparent',
  });

  return (
    <div
      className="h-full overflow-y-auto p-5"
      style={{ color: text_primary }}
    >
      {/* Mode Toggle */}
      <section className="mb-5">
        <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: text_secondary }}>
          Mode
        </label>
        <div className="flex gap-2">
          <button
            data-testid="mode-inspection"
            onClick={() => handleModeChange('inspection')}
            className="px-4 py-2 text-sm rounded border transition-all duration-150 font-medium"
            style={modeButtonStyle(config.mode === 'inspection')}
          >
            Inspection
          </button>
          <button
            data-testid="mode-align"
            onClick={() => handleModeChange('align')}
            className="px-4 py-2 text-sm rounded border transition-all duration-150 font-medium"
            style={modeButtonStyle(config.mode === 'align')}
          >
            Align
          </button>
        </div>
      </section>

      {/* Max Iteration */}
      <section className="mb-5">
        <label className="block text-xs font-medium mb-2 uppercase tracking-wider" style={{ color: text_secondary }}>
          Max Iteration
          <span className="ml-2 normal-case font-normal" style={{ color: text_secondary }}>
            (1 – 20)
          </span>
        </label>
        <input
          data-testid="max-iteration-input"
          type="number"
          min={1}
          max={20}
          value={config.max_iteration}
          onChange={(e) => handleMaxIterationChange(e.target.value)}
          className="w-28 px-3 py-1.5 text-sm rounded border bg-transparent transition-all duration-150 focus:outline-none"
          style={{ borderColor: border_emphasis, color: text_primary }}
        />
      </section>

      {/* Success Criteria */}
      <section className="mb-5">
        <label className="block text-xs font-medium mb-3 uppercase tracking-wider" style={{ color: text_secondary }}>
          Success Criteria
        </label>

        {config.mode === 'inspection' ? (
          <div className="space-y-3">
            {(['accuracy', 'fp_rate', 'fn_rate'] as const).map((field) => (
              <div key={field} className="flex items-center gap-3">
                <span className="w-20 text-xs font-mono" style={{ color: text_secondary }}>
                  {field}
                </span>
                <input
                  data-testid={`criteria-${field}`}
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={criteria[field] ?? ''}
                  onChange={(e) => handleCriteriaChange(field, e.target.value)}
                  className="w-28 px-3 py-1.5 text-sm rounded border bg-transparent transition-all duration-150 focus:outline-none"
                  style={{ borderColor: border_default, color: text_primary }}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {(['coord_error', 'success_rate'] as const).map((field) => (
              <div key={field} className="flex items-center gap-3">
                <span className="w-24 text-xs font-mono" style={{ color: text_secondary }}>
                  {field}
                </span>
                <input
                  data-testid={`criteria-${field}`}
                  type="number"
                  min={0}
                  step={0.01}
                  value={criteria[field] ?? ''}
                  onChange={(e) => handleCriteriaChange(field, e.target.value)}
                  className="w-28 px-3 py-1.5 text-sm rounded border bg-transparent transition-all duration-150 focus:outline-none"
                  style={{ borderColor: border_default, color: text_primary }}
                />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div
          data-testid="warnings-container"
          className="mb-4 p-3 rounded border bg-white/5 backdrop-blur-sm space-y-1"
          style={{ borderColor: accent_warning }}
        >
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <AlertTriangle size={13} style={{ color: accent_warning }} className="mt-0.5 shrink-0" />
              <span style={{ color: accent_warning }}>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Feedback */}
      {saveState === 'success' && (
        <div data-testid="save-success" className="mb-3 flex items-center gap-1.5 text-xs">
          <CheckCircle size={13} style={{ color: accent_success }} />
          <span style={{ color: accent_success }}>Saved successfully</span>
        </div>
      )}
      {saveState === 'error' && (
        <div data-testid="save-error" className="mb-3 text-xs" style={{ color: accent_error }}>
          {saveError || 'Save failed'}
        </div>
      )}

      {/* Save Button */}
      <button
        data-testid="save-config-btn"
        onClick={handleSave}
        disabled={saveState === 'loading'}
        className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 disabled:opacity-50 bg-white/5 backdrop-blur-sm"
        style={{ borderColor: border_default, color: text_primary }}
      >
        {saveState === 'loading' ? (
          <span data-testid="save-loading" className="flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            Saving…
          </span>
        ) : (
          <>
            <Save size={14} />
            Save Config
          </>
        )}
      </button>
    </div>
  );
}
