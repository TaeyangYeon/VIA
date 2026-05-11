import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import LogPanel from '../components/panels/LogPanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';

const { mockGetLogs, mockGetLogAgents, mockClearLogs } = vi.hoisted(() => ({
  mockGetLogs: vi.fn(),
  mockGetLogAgents: vi.fn(),
  mockClearLogs: vi.fn(),
}));

vi.mock('../services/api', () => ({
  getLogs: mockGetLogs,
  getLogAgents: mockGetLogAgents,
  clearLogs: mockClearLogs,
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

const SAMPLE_LOGS = [
  { timestamp: '2026-05-05T10:30:00.123Z', agent: 'orchestrator', level: 'INFO', message: 'Execution started' },
  { timestamp: '2026-05-05T10:30:01.456Z', agent: 'spec', level: 'DEBUG', message: 'Parsing spec' },
  { timestamp: '2026-05-05T10:30:02.789Z', agent: 'algorithm_coder', level: 'WARNING', message: 'Slow iteration' },
  { timestamp: '2026-05-05T10:30:03.000Z', agent: 'vision_judge', level: 'ERROR', message: 'Threshold exceeded' },
];

const RUNNING_EXECUTION_STATE = {
  status: 'running' as const,
  execution_id: 'exec-1',
  current_agent: null,
  current_iteration: 0,
  goal_validation: [],
  progress: 0,
};

const createTestStore = (preloadedState?: any) =>
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
    preloadedState: preloadedState as any,
  });

const renderLogPanel = (preloadedState?: any) => {
  const store = createTestStore(preloadedState);
  const result = render(
    <Provider store={store}>
      <LogPanel />
    </Provider>,
  );
  return { ...result, store };
};

// ── Rendering ──────────────────────────────────────────────────

describe('LogPanel — rendering', () => {
  beforeEach(() => {
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    mockGetLogAgents.mockResolvedValue({ agents: [] });
  });

  it('renders refresh-btn', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('refresh-btn')).toBeInTheDocument());
  });

  it('renders clear-btn', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('clear-btn')).toBeInTheDocument());
  });

  it('renders log-count', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('log-count')).toBeInTheDocument());
  });

  it('shows empty-state when no logs', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeInTheDocument());
  });

  it('renders agent-filter select', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('agent-filter')).toBeInTheDocument());
  });

  it('renders level-filter select', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('level-filter')).toBeInTheDocument());
  });

  it('log-count shows 0 when no logs', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(screen.getByTestId('log-count').textContent).toContain('0');
    });
  });
});

// ── Loading state ──────────────────────────────────────────────

describe('LogPanel — loading state', () => {
  it('shows logs-loading while getLogs is pending', async () => {
    let resolve!: (v: { logs: typeof SAMPLE_LOGS; total: number }) => void;
    mockGetLogs.mockReturnValue(new Promise((r) => { resolve = r; }));
    mockGetLogAgents.mockResolvedValue({ agents: [] });
    renderLogPanel();
    expect(screen.getByTestId('logs-loading')).toBeInTheDocument();
    await act(async () => { resolve({ logs: SAMPLE_LOGS, total: SAMPLE_LOGS.length }); });
    await waitFor(() => {
      expect(screen.queryByTestId('logs-loading')).not.toBeInTheDocument();
    });
  });
});

// ── Error state ────────────────────────────────────────────────

describe('LogPanel — error state', () => {
  it('shows logs-error when getLogs fails on mount', async () => {
    mockGetLogs.mockRejectedValue(new Error('Network error'));
    mockGetLogAgents.mockResolvedValue({ agents: [] });
    renderLogPanel();
    await waitFor(() => {
      expect(screen.getByTestId('logs-error')).toBeInTheDocument();
    });
  });
});

// ── Log entries ────────────────────────────────────────────────

describe('LogPanel — log entries', () => {
  beforeEach(() => {
    mockGetLogs.mockResolvedValue({ logs: SAMPLE_LOGS, total: SAMPLE_LOGS.length });
    mockGetLogAgents.mockResolvedValue({ agents: ['orchestrator', 'spec', 'algorithm_coder', 'vision_judge'] });
  });

  it('renders correct number of log entries', async () => {
    renderLogPanel();
    await waitFor(() => {
      for (let i = 0; i < SAMPLE_LOGS.length; i++) {
        expect(screen.getByTestId(`log-entry-${i}`)).toBeInTheDocument();
      }
    });
  });

  it('does not show empty-state when logs exist', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument();
    });
  });

  it('renders agent-badge for each entry', async () => {
    renderLogPanel();
    await waitFor(() => {
      for (let i = 0; i < SAMPLE_LOGS.length; i++) {
        expect(screen.getByTestId(`agent-badge-${i}`)).toBeInTheDocument();
      }
    });
  });

  it('renders level-badge for each entry', async () => {
    renderLogPanel();
    await waitFor(() => {
      for (let i = 0; i < SAMPLE_LOGS.length; i++) {
        expect(screen.getByTestId(`level-badge-${i}`)).toBeInTheDocument();
      }
    });
  });

  it('agent-badge text matches the agent name', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(screen.getByTestId('agent-badge-0').textContent).toContain('orchestrator');
    });
  });

  it('level-badge text matches the level', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(screen.getByTestId('level-badge-0').textContent).toContain('INFO');
    });
  });

  it('log-count shows the correct total', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(screen.getByTestId('log-count').textContent).toContain('4');
    });
  });

  it('log entry displays the message text', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(screen.getByTestId('log-entry-0').textContent).toContain('Execution started');
    });
  });
});

// ── Timestamp formatting ───────────────────────────────────────

describe('LogPanel — timestamp formatting', () => {
  it('formats timestamp as HH:MM:SS.mmm', async () => {
    const logs = [{ timestamp: '2026-05-05T10:30:00.123Z', agent: 'orchestrator', level: 'INFO', message: 'test' }];
    mockGetLogs.mockResolvedValue({ logs, total: 1 });
    mockGetLogAgents.mockResolvedValue({ agents: ['orchestrator'] });
    renderLogPanel();
    await waitFor(() => {
      const entry = screen.getByTestId('log-entry-0');
      expect(entry.textContent).toMatch(/\d{2}:\d{2}:\d{2}\.\d{3}/);
    });
  });
});

// ── Agent filter ───────────────────────────────────────────────

describe('LogPanel — agent filter', () => {
  beforeEach(() => {
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    mockGetLogAgents.mockResolvedValue({ agents: ['orchestrator', 'spec'] });
  });

  it('calls getLogAgents on mount', async () => {
    renderLogPanel();
    await waitFor(() => {
      expect(mockGetLogAgents).toHaveBeenCalledTimes(1);
    });
  });

  it('agent filter contains "All Agents" option', async () => {
    renderLogPanel();
    await waitFor(() => {
      const select = screen.getByTestId('agent-filter');
      expect(select.textContent).toContain('All Agents');
    });
  });

  it('agent filter contains agents returned from API', async () => {
    renderLogPanel();
    await waitFor(() => {
      const select = screen.getByTestId('agent-filter');
      expect(select.textContent).toContain('orchestrator');
      expect(select.textContent).toContain('spec');
    });
  });

  it('selecting an agent calls getLogs with agent param', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('agent-filter')).toBeInTheDocument());
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    await act(async () => {
      fireEvent.change(screen.getByTestId('agent-filter'), { target: { value: 'orchestrator' } });
    });
    await waitFor(() => {
      expect(mockGetLogs).toHaveBeenCalledWith(expect.objectContaining({ agent: 'orchestrator' }));
    });
  });
});

// ── Level filter ───────────────────────────────────────────────

describe('LogPanel — level filter', () => {
  beforeEach(() => {
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    mockGetLogAgents.mockResolvedValue({ agents: [] });
  });

  it('level filter contains "All Levels" option', async () => {
    renderLogPanel();
    await waitFor(() => {
      const select = screen.getByTestId('level-filter');
      expect(select.textContent).toContain('All Levels');
    });
  });

  it('level filter contains DEBUG, INFO, WARNING, ERROR options', async () => {
    renderLogPanel();
    await waitFor(() => {
      const select = screen.getByTestId('level-filter');
      expect(select.textContent).toContain('DEBUG');
      expect(select.textContent).toContain('INFO');
      expect(select.textContent).toContain('WARNING');
      expect(select.textContent).toContain('ERROR');
    });
  });

  it('selecting a level calls getLogs with level param', async () => {
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('level-filter')).toBeInTheDocument());
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    await act(async () => {
      fireEvent.change(screen.getByTestId('level-filter'), { target: { value: 'ERROR' } });
    });
    await waitFor(() => {
      expect(mockGetLogs).toHaveBeenCalledWith(expect.objectContaining({ level: 'ERROR' }));
    });
  });
});

// ── Manual refresh ─────────────────────────────────────────────

describe('LogPanel — manual refresh', () => {
  it('clicking refresh-btn calls getLogs', async () => {
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    mockGetLogAgents.mockResolvedValue({ agents: [] });
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('refresh-btn')).toBeInTheDocument());
    mockGetLogs.mockClear();
    await act(async () => {
      fireEvent.click(screen.getByTestId('refresh-btn'));
    });
    await waitFor(() => {
      expect(mockGetLogs).toHaveBeenCalledTimes(1);
    });
  });
});

// ── Clear logs ─────────────────────────────────────────────────

describe('LogPanel — clear logs', () => {
  it('clicking clear-btn calls clearLogs API', async () => {
    mockGetLogs.mockResolvedValue({ logs: SAMPLE_LOGS, total: SAMPLE_LOGS.length });
    mockGetLogAgents.mockResolvedValue({ agents: [] });
    mockClearLogs.mockResolvedValue({ cleared: true });
    renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('clear-btn')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('clear-btn'));
    });
    await waitFor(() => {
      expect(mockClearLogs).toHaveBeenCalledTimes(1);
    });
  });

  it('after clear-btn click Redux logs entries are empty', async () => {
    mockGetLogs.mockResolvedValue({ logs: SAMPLE_LOGS, total: SAMPLE_LOGS.length });
    mockGetLogAgents.mockResolvedValue({ agents: [] });
    mockClearLogs.mockResolvedValue({ cleared: true });
    const { store } = renderLogPanel();
    await waitFor(() => expect(screen.getByTestId('clear-btn')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('clear-btn'));
    });
    await waitFor(() => {
      expect(store.getState().logs.entries).toHaveLength(0);
    });
  });
});

// ── Polling ────────────────────────────────────────────────────

describe('LogPanel — polling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockGetLogAgents.mockResolvedValue({ agents: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('polls getLogs every 2 seconds when execution is running', async () => {
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    renderLogPanel({ execution: RUNNING_EXECUTION_STATE });

    await act(async () => {
      await Promise.resolve();
    });

    const callsBefore = mockGetLogs.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(mockGetLogs.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it('does not start polling when execution is idle', async () => {
    mockGetLogs.mockResolvedValue({ logs: [], total: 0 });
    renderLogPanel();

    await act(async () => {
      await Promise.resolve();
    });

    const callsAfterMount = mockGetLogs.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(6000);
      await Promise.resolve();
    });

    expect(mockGetLogs.mock.calls.length).toBe(callsAfterMount);
  });
});

// ── Agent color determinism ────────────────────────────────────

describe('LogPanel — agent color determinism', () => {
  it('same agent always gets the same badge color', async () => {
    const logs = [
      { timestamp: '2026-05-05T10:30:00.000Z', agent: 'orchestrator', level: 'INFO', message: 'msg 1' },
      { timestamp: '2026-05-05T10:30:01.000Z', agent: 'orchestrator', level: 'INFO', message: 'msg 2' },
    ];
    mockGetLogs.mockResolvedValue({ logs, total: 2 });
    mockGetLogAgents.mockResolvedValue({ agents: ['orchestrator'] });
    renderLogPanel();
    await waitFor(() => {
      const badge0 = screen.getByTestId('agent-badge-0');
      const badge1 = screen.getByTestId('agent-badge-1');
      expect(badge0.style.color).toBe(badge1.style.color);
    });
  });
});
