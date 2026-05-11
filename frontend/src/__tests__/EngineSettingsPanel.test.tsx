import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import EngineSettingsPanel from '../components/panels/EngineSettingsPanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';
import engineReducer from '../store/slices/engineSlice';

const { mockGetEngineStatus, mockSaveEngineConfig, mockDownloadSetupNotebook } = vi.hoisted(() => ({
  mockGetEngineStatus: vi.fn(),
  mockSaveEngineConfig: vi.fn(),
  mockDownloadSetupNotebook: vi.fn(),
}));

vi.mock('../services/api', () => ({
  getEngineStatus: mockGetEngineStatus,
  saveEngineConfig: mockSaveEngineConfig,
  downloadSetupNotebook: mockDownloadSetupNotebook,
}));

afterEach(() => {
  vi.clearAllMocks();
});

const createTestStore = () =>
  configureStore({
    reducer: {
      project: projectReducer,
      images: imagesReducer,
      config: configReducer,
      directives: directivesReducer,
      execution: executionReducer,
      result: resultReducer,
      logs: logsReducer,
      engine: engineReducer,
    },
  });

const renderPanel = () => {
  const store = createTestStore();
  const result = render(
    <Provider store={store}>
      <EngineSettingsPanel />
    </Provider>,
  );
  return { ...result, store };
};

const LOCAL_STATUS = {
  engine_mode: 'local',
  base_url: 'http://localhost:11434',
  connected: true,
  model_available: true,
  error: null,
};

const LOCAL_DISCONNECTED = {
  engine_mode: 'local',
  base_url: 'http://localhost:11434',
  connected: false,
  model_available: false,
  error: null,
};

const COLAB_STATUS = {
  engine_mode: 'colab',
  base_url: 'https://xxx.trycloudflare.com',
  connected: true,
  model_available: true,
  error: null,
};

// ── Rendering ──────────────────────────────────────────────────

describe('EngineSettingsPanel — rendering', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
  });

  it('renders mode-local button', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('mode-local')).toBeInTheDocument();
    });
  });

  it('renders mode-colab button', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('mode-colab')).toBeInTheDocument();
    });
  });

  it('renders local-status section by default', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-status')).toBeInTheDocument();
    });
  });

  it('does not render colab-section by default', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('mode-local')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('colab-section')).not.toBeInTheDocument();
  });

  it('renders save-engine-btn', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('save-engine-btn')).toBeInTheDocument();
    });
  });
});

// ── Mount behavior ─────────────────────────────────────────────

describe('EngineSettingsPanel — on mount', () => {
  it('calls getEngineStatus once on mount', async () => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
    renderPanel();
    await waitFor(() => {
      expect(mockGetEngineStatus).toHaveBeenCalledTimes(1);
    });
  });

  it('initializes to local mode when backend returns local', async () => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
    const { store } = renderPanel();
    await waitFor(() => {
      expect(store.getState().engine.engine_mode).toBe('local');
    });
  });

  it('initializes to colab mode when backend returns colab', async () => {
    mockGetEngineStatus.mockResolvedValue(COLAB_STATUS);
    const { store } = renderPanel();
    await waitFor(() => {
      expect(store.getState().engine.engine_mode).toBe('colab');
    });
  });

  it('sets connection_status to connected when backend says connected', async () => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
    const { store } = renderPanel();
    await waitFor(() => {
      expect(store.getState().engine.connection_status).toBe('connected');
    });
  });

  it('sets connection_status to disconnected when backend says not connected', async () => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_DISCONNECTED);
    const { store } = renderPanel();
    await waitFor(() => {
      expect(store.getState().engine.connection_status).toBe('disconnected');
    });
  });

  it('handles getEngineStatus failure gracefully', async () => {
    mockGetEngineStatus.mockRejectedValue(new Error('Connection refused'));
    const { store } = renderPanel();
    await waitFor(() => {
      expect(store.getState().engine.connection_status).toBe('disconnected');
    });
    expect(screen.queryByTestId('local-status')).toBeInTheDocument();
  });
});

// ── Local mode ─────────────────────────────────────────────────

describe('EngineSettingsPanel — local mode', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
  });

  it('renders local-connection-badge', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-connection-badge')).toBeInTheDocument();
    });
  });

  it('shows Connected in badge when status is connected', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-connection-badge')).toHaveTextContent('Connected');
    });
  });

  it('shows Disconnected in badge when status is disconnected', async () => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_DISCONNECTED);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-connection-badge')).toHaveTextContent('Disconnected');
    });
  });

  it('renders local-model-status', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-model-status')).toBeInTheDocument();
    });
  });

  it('shows gemma4:e4b ready in model status when connected', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-model-status')).toHaveTextContent('gemma4:e4b ready');
    });
  });

  it('shows Model not found when disconnected', async () => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_DISCONNECTED);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('local-model-status')).toHaveTextContent('Model not found');
    });
  });
});

// ── Mode switching ─────────────────────────────────────────────

describe('EngineSettingsPanel — mode switching', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
  });

  it('clicking mode-colab shows colab-section', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.getByTestId('colab-section')).toBeInTheDocument();
  });

  it('clicking mode-colab hides local-status', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.queryByTestId('local-status')).not.toBeInTheDocument();
  });

  it('clicking mode-local shows local-status', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.click(screen.getByTestId('mode-local'));
    expect(screen.getByTestId('local-status')).toBeInTheDocument();
  });

  it('clicking mode-local hides colab-section', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.click(screen.getByTestId('mode-local'));
    expect(screen.queryByTestId('colab-section')).not.toBeInTheDocument();
  });

  it('dispatches setEngineMode(colab) when clicking mode-colab', async () => {
    const { store } = renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(store.getState().engine.engine_mode).toBe('colab');
  });

  it('dispatches setEngineMode(local) when clicking mode-local from colab', async () => {
    const { store } = renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.click(screen.getByTestId('mode-local'));
    expect(store.getState().engine.engine_mode).toBe('local');
  });
});

// ── Colab mode UI ──────────────────────────────────────────────

describe('EngineSettingsPanel — colab mode UI', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
  });

  it('renders model-select with gemma4:e4b option', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    const select = screen.getByTestId('model-select') as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toContain('gemma4:e4b');
  });

  it('renders model-select with gemma4:27b option', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    const select = screen.getByTestId('model-select') as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toContain('gemma4:27b');
  });

  it('renders download-notebook-btn', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.getByTestId('download-notebook-btn')).toBeInTheDocument();
  });

  it('renders setup-guide with Korean instructions', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.getByTestId('setup-guide')).toBeInTheDocument();
    expect(screen.getByTestId('setup-guide')).toHaveTextContent('Google Colab');
  });

  it('renders colab-url-input', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.getByTestId('colab-url-input')).toBeInTheDocument();
  });

  it('renders test-connection-btn', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.getByTestId('test-connection-btn')).toBeInTheDocument();
  });
});

// ── Download notebook ──────────────────────────────────────────

describe('EngineSettingsPanel — download notebook', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
    mockDownloadSetupNotebook.mockResolvedValue(undefined);
  });

  it('calls downloadSetupNotebook with selected model on button click', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('download-notebook-btn'));
    });
    await waitFor(() => {
      expect(mockDownloadSetupNotebook).toHaveBeenCalledWith('gemma4:e4b');
    });
  });

  it('calls downloadSetupNotebook with gemma4:27b when that model is selected', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.change(screen.getByTestId('model-select'), { target: { value: 'gemma4:27b' } });
    await act(async () => {
      fireEvent.click(screen.getByTestId('download-notebook-btn'));
    });
    await waitFor(() => {
      expect(mockDownloadSetupNotebook).toHaveBeenCalledWith('gemma4:27b');
    });
  });
});

// ── Connection test ────────────────────────────────────────────

describe('EngineSettingsPanel — connection test', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
  });

  it('does not show connection-status div initially (disconnected)', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    expect(screen.queryByTestId('connection-status')).not.toBeInTheDocument();
  });

  it('dispatches connecting then connected on successful test', async () => {
    mockSaveEngineConfig.mockResolvedValue({
      engine_mode: 'colab',
      base_url: 'https://xxx.trycloudflare.com',
      warnings: [],
    });
    const { store } = renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.change(screen.getByTestId('colab-url-input'), {
      target: { value: 'https://xxx.trycloudflare.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-connection-btn'));
    });
    await waitFor(() => {
      expect(store.getState().engine.connection_status).toBe('connected');
    });
  });

  it('shows connection-status div with Connected text on success', async () => {
    mockSaveEngineConfig.mockResolvedValue({
      engine_mode: 'colab',
      base_url: 'https://xxx.trycloudflare.com',
      warnings: [],
    });
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.change(screen.getByTestId('colab-url-input'), {
      target: { value: 'https://xxx.trycloudflare.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-connection-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('connection-status')).toHaveTextContent('Connected');
    });
  });

  it('dispatches error status on failed connection test', async () => {
    mockSaveEngineConfig.mockRejectedValue(new Error('Cannot reach host'));
    const { store } = renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.change(screen.getByTestId('colab-url-input'), {
      target: { value: 'https://bad-url.example.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-connection-btn'));
    });
    await waitFor(() => {
      expect(store.getState().engine.connection_status).toBe('error');
    });
  });

  it('shows error message in connection-status on failure', async () => {
    mockSaveEngineConfig.mockRejectedValue(new Error('Cannot reach host'));
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.change(screen.getByTestId('colab-url-input'), {
      target: { value: 'https://bad-url.example.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-connection-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('connection-status')).toHaveTextContent('Cannot reach host');
    });
  });

  it('calls saveEngineConfig with colab engine_mode and URL', async () => {
    mockSaveEngineConfig.mockResolvedValue({
      engine_mode: 'colab',
      base_url: 'https://xxx.trycloudflare.com',
    });
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('mode-colab')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-colab'));
    fireEvent.change(screen.getByTestId('colab-url-input'), {
      target: { value: 'https://xxx.trycloudflare.com' },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('test-connection-btn'));
    });
    await waitFor(() => {
      expect(mockSaveEngineConfig).toHaveBeenCalledWith({
        engine_mode: 'colab',
        colab_url: 'https://xxx.trycloudflare.com',
      });
    });
  });
});

// ── Save button ────────────────────────────────────────────────

describe('EngineSettingsPanel — save button', () => {
  beforeEach(() => {
    mockGetEngineStatus.mockResolvedValue(LOCAL_STATUS);
  });

  it('calls saveEngineConfig on save-engine-btn click', async () => {
    mockSaveEngineConfig.mockResolvedValue({
      engine_mode: 'local',
      base_url: 'http://localhost:11434',
    });
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('save-engine-btn')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-engine-btn'));
    });
    await waitFor(() => {
      expect(mockSaveEngineConfig).toHaveBeenCalledWith(
        expect.objectContaining({ engine_mode: 'local' }),
      );
    });
  });

  it('shows save-success after successful save', async () => {
    mockSaveEngineConfig.mockResolvedValue({
      engine_mode: 'local',
      base_url: 'http://localhost:11434',
    });
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('save-engine-btn')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-engine-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('save-success')).toBeInTheDocument();
    });
  });

  it('shows save-error when save fails', async () => {
    mockSaveEngineConfig.mockRejectedValue(new Error('Save failed'));
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('save-engine-btn')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-engine-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('save-error')).toBeInTheDocument();
    });
  });
});
