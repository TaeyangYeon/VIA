import React, { useEffect, useState } from 'react';
import {
  Monitor,
  Cloud,
  Download,
  CheckCircle,
  XCircle,
  Loader2,
  Save,
} from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import {
  selectEngine,
  setEngineMode,
  setColabUrl,
  setConnectionStatus,
  setRemoteInfo,
  setEngineError,
} from '../../store/slices/engineSlice';
import { getEngineStatus, saveEngineConfig, downloadSetupNotebook } from '../../services/api';
import {
  bg_secondary,
  border_default,
  border_emphasis,
  text_primary,
  text_secondary,
  accent_success,
  accent_error,
} from '../../styles/design-tokens';

const MODELS = ['gemma4:e4b', 'gemma4:27b'];

export default function EngineSettingsPanel() {
  const dispatch = useAppDispatch();
  const engine = useAppSelector(selectEngine);
  const [colabUrlInput, setColabUrlInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemma4:e4b');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState('');

  useEffect(() => {
    getEngineStatus()
      .then((status) => {
        dispatch(setEngineMode(status.engine_mode as 'local' | 'colab'));
        if (status.engine_mode === 'colab') {
          dispatch(setColabUrl(status.base_url));
          setColabUrlInput(status.base_url);
        }
        dispatch(setConnectionStatus(status.connected ? 'connected' : 'disconnected'));
        if (status.error) {
          dispatch(setEngineError(status.error));
        }
      })
      .catch(() => {
        dispatch(setConnectionStatus('disconnected'));
      });
  }, [dispatch]);

  const handleModeChange = (mode: 'local' | 'colab') => {
    dispatch(setEngineMode(mode));
    dispatch(setConnectionStatus('disconnected'));
    dispatch(setRemoteInfo(null));
    dispatch(setEngineError(null));
  };

  const handleTestConnection = async () => {
    dispatch(setConnectionStatus('connecting'));
    dispatch(setEngineError(null));
    try {
      await saveEngineConfig({ engine_mode: 'colab', colab_url: colabUrlInput });
      dispatch(setColabUrl(colabUrlInput));
      dispatch(setConnectionStatus('connected'));
      dispatch(setRemoteInfo(null));
    } catch (err: any) {
      dispatch(setConnectionStatus('error'));
      dispatch(setEngineError(err?.message ?? 'Connection failed'));
    }
  };

  const handleDownload = async () => {
    await downloadSetupNotebook(selectedModel);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    setSaveError('');
    try {
      const config: { engine_mode: string; colab_url?: string } = {
        engine_mode: engine.engine_mode,
      };
      if (engine.engine_mode === 'colab' && engine.colab_url) {
        config.colab_url = engine.colab_url;
      }
      await saveEngineConfig(config);
      setSaveSuccess(true);
    } catch (err: any) {
      setSaveError(err?.message ?? 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const modeButtonStyle = (active: boolean) => ({
    borderColor: active ? text_primary : border_default,
    color: active ? text_primary : text_secondary,
    backgroundColor: active ? bg_secondary : 'transparent',
  });

  return (
    <div className="h-full overflow-y-auto p-5" style={{ color: text_primary }}>
      {/* Mode Toggle */}
      <section className="mb-5">
        <label
          className="block text-xs font-medium mb-2 uppercase tracking-wider"
          style={{ color: text_secondary }}
        >
          Engine Mode
        </label>
        <div className="flex gap-2">
          <button
            data-testid="mode-local"
            onClick={() => handleModeChange('local')}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 font-medium"
            style={modeButtonStyle(engine.engine_mode === 'local')}
          >
            <Monitor size={14} />
            Local
          </button>
          <button
            data-testid="mode-colab"
            onClick={() => handleModeChange('colab')}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 font-medium"
            style={modeButtonStyle(engine.engine_mode === 'colab')}
          >
            <Cloud size={14} />
            Colab
          </button>
        </div>
      </section>

      {/* Local Mode Section */}
      {engine.engine_mode === 'local' && (
        <section
          data-testid="local-status"
          className="mb-5 p-4 rounded bg-white/5 backdrop-blur-sm border"
          style={{ borderColor: border_default }}
        >
          <div className="flex items-center justify-between mb-3">
            <span
              className="text-xs font-medium uppercase tracking-wider"
              style={{ color: text_secondary }}
            >
              Local Ollama
            </span>
            <span
              data-testid="local-connection-badge"
              className="px-2 py-0.5 text-xs rounded-full"
              style={{
                backgroundColor:
                  engine.connection_status === 'connected'
                    ? `${accent_success}20`
                    : `${accent_error}20`,
                color:
                  engine.connection_status === 'connected' ? accent_success : accent_error,
              }}
            >
              {engine.connection_status === 'connected' ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <p data-testid="local-model-status" className="text-xs" style={{ color: text_secondary }}>
            {engine.connection_status === 'connected' ? 'gemma4:e4b ready' : 'Model not found'}
          </p>
        </section>
      )}

      {/* Colab Mode Section */}
      {engine.engine_mode === 'colab' && (
        <section data-testid="colab-section" className="space-y-4 mb-5">
          {/* Step 1: Download */}
          <div
            className="p-4 rounded bg-white/5 backdrop-blur-sm border"
            style={{ borderColor: border_default }}
          >
            <p
              className="text-xs font-medium uppercase tracking-wider mb-3"
              style={{ color: text_secondary }}
            >
              Step 1 — Download Notebook
            </p>
            <div className="flex items-center gap-3">
              <select
                data-testid="model-select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="px-3 py-1.5 text-sm rounded border bg-transparent transition-all duration-150 focus:outline-none"
                style={{ borderColor: border_default, color: text_primary }}
              >
                {MODELS.map((m) => (
                  <option key={m} value={m} style={{ backgroundColor: '#111111' }}>
                    {m}
                  </option>
                ))}
              </select>
              <button
                data-testid="download-notebook-btn"
                onClick={handleDownload}
                className="flex items-center gap-2 px-4 py-1.5 text-sm rounded border transition-all duration-150 bg-white/5"
                style={{ borderColor: border_default, color: text_primary }}
              >
                <Download size={13} />
                Download
              </button>
            </div>
          </div>

          {/* Step 2: Guide */}
          <div
            data-testid="setup-guide"
            className="p-4 rounded bg-white/5 backdrop-blur-sm border"
            style={{ borderColor: border_default }}
          >
            <p
              className="text-xs font-medium uppercase tracking-wider mb-3"
              style={{ color: text_secondary }}
            >
              Step 2 — Run in Colab
            </p>
            <ol className="space-y-1.5 text-xs" style={{ color: text_secondary }}>
              <li>① Google Colab에서 노트북 열기</li>
              <li>② 런타임 → GPU로 변경 후 전체 실행</li>
              <li>③ 출력된 터널 URL 복사</li>
            </ol>
          </div>

          {/* Step 3: Connect */}
          <div
            className="p-4 rounded bg-white/5 backdrop-blur-sm border"
            style={{ borderColor: border_default }}
          >
            <p
              className="text-xs font-medium uppercase tracking-wider mb-3"
              style={{ color: text_secondary }}
            >
              Step 3 — Connect
            </p>
            <div className="flex items-center gap-3 mb-3">
              <input
                data-testid="colab-url-input"
                type="text"
                placeholder="https://xxx.trycloudflare.com"
                value={colabUrlInput}
                onChange={(e) => setColabUrlInput(e.target.value)}
                className="flex-1 px-3 py-1.5 text-sm rounded border bg-transparent transition-all duration-150 focus:outline-none"
                style={{ borderColor: border_emphasis, color: text_primary }}
              />
              <button
                data-testid="test-connection-btn"
                onClick={handleTestConnection}
                disabled={engine.connection_status === 'connecting'}
                className="flex items-center gap-2 px-4 py-1.5 text-sm rounded border transition-all duration-150 bg-white/5 disabled:opacity-50"
                style={{ borderColor: border_default, color: text_primary }}
              >
                {engine.connection_status === 'connecting' && (
                  <Loader2 size={13} className="animate-spin" />
                )}
                Test
              </button>
            </div>

            {engine.connection_status !== 'disconnected' && (
              <div
                data-testid="connection-status"
                className="flex items-center gap-2 text-xs"
              >
                {engine.connection_status === 'connecting' && (
                  <>
                    <Loader2 size={13} className="animate-spin" style={{ color: text_secondary }} />
                    <span style={{ color: text_secondary }}>Connecting…</span>
                  </>
                )}
                {engine.connection_status === 'connected' && (
                  <>
                    <CheckCircle size={13} style={{ color: accent_success }} />
                    <span style={{ color: accent_success }}>
                      Connected
                      {engine.remote_info?.model_name ? ` — ${engine.remote_info.model_name}` : ''}
                    </span>
                  </>
                )}
                {engine.connection_status === 'error' && (
                  <>
                    <XCircle size={13} style={{ color: accent_error }} />
                    <span style={{ color: accent_error }}>
                      {engine.error ?? 'Connection failed'}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Save */}
      <div className="mt-2">
        {saveSuccess && (
          <div data-testid="save-success" className="mb-3 flex items-center gap-1.5 text-xs">
            <CheckCircle size={13} style={{ color: accent_success }} />
            <span style={{ color: accent_success }}>Saved successfully</span>
          </div>
        )}
        {saveError && (
          <div data-testid="save-error" className="mb-3 text-xs" style={{ color: accent_error }}>
            {saveError}
          </div>
        )}
        <button
          data-testid="save-engine-btn"
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 text-sm rounded border transition-all duration-150 disabled:opacity-50 bg-white/5 backdrop-blur-sm"
          style={{ borderColor: border_default, color: text_primary }}
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save Engine Config
        </button>
      </div>
    </div>
  );
}
