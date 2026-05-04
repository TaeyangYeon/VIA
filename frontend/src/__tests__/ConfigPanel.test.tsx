import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import ConfigPanel from '../components/panels/ConfigPanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';

const { mockSaveConfig, mockGetConfig } = vi.hoisted(() => ({
  mockSaveConfig: vi.fn(),
  mockGetConfig: vi.fn(),
}));

vi.mock('../services/api', () => ({
  saveConfig: mockSaveConfig,
  getConfig: mockGetConfig,
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
    },
  });

const renderConfigPanel = () => {
  const store = createTestStore();
  const result = render(
    <Provider store={store}>
      <ConfigPanel />
    </Provider>,
  );
  return { ...result, store };
};

const DEFAULT_CONFIG = {
  mode: 'inspection' as const,
  max_iteration: 10,
  success_criteria: { accuracy: 0.95, fp_rate: 0.05, fn_rate: 0.05 },
};

// ── Rendering ──────────────────────────────────────────────────

describe('ConfigPanel — rendering', () => {
  beforeEach(() => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
  });

  it('renders mode-inspection and mode-align toggle buttons', async () => {
    renderConfigPanel();
    await waitFor(() => {
      expect(screen.getByTestId('mode-inspection')).toBeInTheDocument();
      expect(screen.getByTestId('mode-align')).toBeInTheDocument();
    });
  });

  it('renders max-iteration-input', async () => {
    renderConfigPanel();
    await waitFor(() => {
      expect(screen.getByTestId('max-iteration-input')).toBeInTheDocument();
    });
  });

  it('renders save-config-btn', async () => {
    renderConfigPanel();
    await waitFor(() => {
      expect(screen.getByTestId('save-config-btn')).toBeInTheDocument();
    });
  });

  it('renders inspection criteria fields when mode is inspection', async () => {
    renderConfigPanel();
    await waitFor(() => {
      expect(screen.getByTestId('criteria-accuracy')).toBeInTheDocument();
      expect(screen.getByTestId('criteria-fp_rate')).toBeInTheDocument();
      expect(screen.getByTestId('criteria-fn_rate')).toBeInTheDocument();
    });
  });
});

// ── Load on mount ──────────────────────────────────────────────

describe('ConfigPanel — load on mount', () => {
  it('calls getConfig once on mount', async () => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
    renderConfigPanel();
    await waitFor(() => {
      expect(mockGetConfig).toHaveBeenCalledTimes(1);
    });
  });

  it('dispatches loaded config to Redux store', async () => {
    const savedConfig = {
      mode: 'align' as const,
      max_iteration: 15,
      success_criteria: { coord_error: 1.5, success_rate: 0.9 },
    };
    mockGetConfig.mockResolvedValue(savedConfig);
    const { store } = renderConfigPanel();
    await waitFor(() => {
      expect(store.getState().config.mode).toBe('align');
      expect(store.getState().config.max_iteration).toBe(15);
    });
  });

  it('handles 404 gracefully without showing load-error', async () => {
    const err = Object.assign(new Error('Not Found'), { response: { status: 404 } });
    mockGetConfig.mockRejectedValue(err);
    const { store } = renderConfigPanel();
    await waitFor(() => {
      expect(store.getState().config.mode).toBe('inspection');
    });
    expect(screen.queryByTestId('load-error')).not.toBeInTheDocument();
  });
});

// ── Mode toggle ────────────────────────────────────────────────

describe('ConfigPanel — mode toggle', () => {
  beforeEach(() => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
  });

  it('inspection mode is active by default', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('mode-inspection')).toBeInTheDocument());
    expect(store.getState().config.mode).toBe('inspection');
  });

  it('clicking mode-align dispatches setMode("align")', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('mode-align')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-align'));
    expect(store.getState().config.mode).toBe('align');
  });

  it('shows align criteria fields after clicking mode-align', async () => {
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('mode-align')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-align'));
    expect(screen.getByTestId('criteria-coord_error')).toBeInTheDocument();
    expect(screen.getByTestId('criteria-success_rate')).toBeInTheDocument();
  });

  it('hides inspection criteria fields after clicking mode-align', async () => {
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('mode-align')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('mode-align'));
    expect(screen.queryByTestId('criteria-accuracy')).not.toBeInTheDocument();
  });
});

// ── Max iteration ──────────────────────────────────────────────

describe('ConfigPanel — max iteration', () => {
  beforeEach(() => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
  });

  it('dispatches setMaxIteration when value is within valid range', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('max-iteration-input')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('max-iteration-input'), { target: { value: '15' } });
    expect(store.getState().config.max_iteration).toBe(15);
  });

  it('does not dispatch for values below minimum (0)', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('max-iteration-input')).toBeInTheDocument());
    const prev = store.getState().config.max_iteration;
    fireEvent.change(screen.getByTestId('max-iteration-input'), { target: { value: '0' } });
    expect(store.getState().config.max_iteration).toBe(prev);
  });

  it('does not dispatch for values above maximum (21)', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('max-iteration-input')).toBeInTheDocument());
    const prev = store.getState().config.max_iteration;
    fireEvent.change(screen.getByTestId('max-iteration-input'), { target: { value: '21' } });
    expect(store.getState().config.max_iteration).toBe(prev);
  });
});

// ── Success criteria ───────────────────────────────────────────

describe('ConfigPanel — success criteria', () => {
  beforeEach(() => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
  });

  it('dispatches updated success_criteria when accuracy changes', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('criteria-accuracy')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('criteria-accuracy'), { target: { value: '0.98' } });
    expect((store.getState().config.success_criteria as any).accuracy).toBe(0.98);
  });

  it('dispatches updated success_criteria when fp_rate changes', async () => {
    const { store } = renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('criteria-fp_rate')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('criteria-fp_rate'), { target: { value: '0.03' } });
    expect((store.getState().config.success_criteria as any).fp_rate).toBe(0.03);
  });
});

// ── Save config ────────────────────────────────────────────────

describe('ConfigPanel — save config', () => {
  beforeEach(() => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
  });

  it('calls saveConfig with current Redux state', async () => {
    mockSaveConfig.mockResolvedValue({ config: DEFAULT_CONFIG, warnings: [] });
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('save-config-btn')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-config-btn'));
    });
    await waitFor(() => {
      expect(mockSaveConfig).toHaveBeenCalledWith(expect.objectContaining({ mode: 'inspection' }));
    });
  });

  it('shows save-loading while saveConfig is pending', async () => {
    let resolve!: (v: any) => void;
    mockSaveConfig.mockReturnValue(new Promise((r) => { resolve = r; }));
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('save-config-btn')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('save-config-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('save-loading')).toBeInTheDocument();
    });
    await act(async () => { resolve({ config: DEFAULT_CONFIG, warnings: [] }); });
  });

  it('shows save-success after successful save', async () => {
    mockSaveConfig.mockResolvedValue({ config: DEFAULT_CONFIG, warnings: [] });
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('save-config-btn')).toBeInTheDocument());
    await act(async () => { fireEvent.click(screen.getByTestId('save-config-btn')); });
    await waitFor(() => {
      expect(screen.getByTestId('save-success')).toBeInTheDocument();
    });
  });

  it('shows save-error when saveConfig fails', async () => {
    mockSaveConfig.mockRejectedValue(new Error('Network error'));
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('save-config-btn')).toBeInTheDocument());
    await act(async () => { fireEvent.click(screen.getByTestId('save-config-btn')); });
    await waitFor(() => {
      expect(screen.getByTestId('save-error')).toBeInTheDocument();
    });
  });
});

// ── Extreme goal warnings ──────────────────────────────────────

describe('ConfigPanel — extreme goal warnings', () => {
  beforeEach(() => {
    mockGetConfig.mockResolvedValue(DEFAULT_CONFIG);
  });

  it('displays warnings returned from saveConfig', async () => {
    const warnings = ['accuracy > 0.99 is extremely difficult'];
    mockSaveConfig.mockResolvedValue({ config: DEFAULT_CONFIG, warnings });
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('save-config-btn')).toBeInTheDocument());
    await act(async () => { fireEvent.click(screen.getByTestId('save-config-btn')); });
    await waitFor(() => {
      expect(screen.getByTestId('warnings-container')).toBeInTheDocument();
      expect(screen.getByText('accuracy > 0.99 is extremely difficult')).toBeInTheDocument();
    });
  });

  it('does not render warnings-container when no warnings', async () => {
    mockSaveConfig.mockResolvedValue({ config: DEFAULT_CONFIG, warnings: [] });
    renderConfigPanel();
    await waitFor(() => expect(screen.getByTestId('save-config-btn')).toBeInTheDocument());
    await act(async () => { fireEvent.click(screen.getByTestId('save-config-btn')); });
    await waitFor(() => {
      expect(screen.getByTestId('save-success')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('warnings-container')).not.toBeInTheDocument();
  });
});
