import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import ExecutionPanel from '../components/panels/ExecutionPanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';

const { mockStartExecution, mockGetExecutionStatus, mockCancelExecution } = vi.hoisted(() => ({
  mockStartExecution: vi.fn(),
  mockGetExecutionStatus: vi.fn(),
  mockCancelExecution: vi.fn(),
}));

vi.mock('../services/api', () => ({
  startExecution: mockStartExecution,
  getExecutionStatus: mockGetExecutionStatus,
  cancelExecution: mockCancelExecution,
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

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

const renderExecutionPanel = (executionState?: Partial<typeof RUNNING_EXECUTION_STATE> & { status?: string }) => {
  const preloadedState = executionState ? { execution: executionState } : undefined;
  const store = createTestStore(preloadedState);
  const result = render(
    <Provider store={store}>
      <ExecutionPanel />
    </Provider>,
  );
  return { ...result, store };
};

// ── Rendering ──────────────────────────────────────────────────

describe('ExecutionPanel — rendering', () => {
  it('renders purpose-textarea', () => {
    renderExecutionPanel();
    expect(screen.getByTestId('purpose-textarea')).toBeInTheDocument();
  });

  it('renders start-btn', () => {
    renderExecutionPanel();
    expect(screen.getByTestId('start-btn')).toBeInTheDocument();
  });

  it('shows idle-state message when no execution has started', () => {
    renderExecutionPanel();
    expect(screen.getByTestId('idle-state')).toBeInTheDocument();
  });

  it('start-btn is disabled when purpose textarea is empty', () => {
    renderExecutionPanel();
    expect(screen.getByTestId('start-btn')).toBeDisabled();
  });

  it('start-btn is enabled after entering purpose text', () => {
    renderExecutionPanel();
    fireEvent.change(screen.getByTestId('purpose-textarea'), { target: { value: '불량 검출' } });
    expect(screen.getByTestId('start-btn')).not.toBeDisabled();
  });
});

// ── Start execution ────────────────────────────────────────────

describe('ExecutionPanel — start execution', () => {
  it('calls startExecution with the purpose text', async () => {
    mockStartExecution.mockResolvedValue({ execution_id: 'exec-1', status: 'running' });
    renderExecutionPanel();
    fireEvent.change(screen.getByTestId('purpose-textarea'), { target: { value: '불량 검출' } });
    await act(async () => { fireEvent.click(screen.getByTestId('start-btn')); });
    await waitFor(() => {
      expect(mockStartExecution).toHaveBeenCalledWith('불량 검출');
    });
  });

  it('dispatches setExecutionId after successful start', async () => {
    mockStartExecution.mockResolvedValue({ execution_id: 'exec-1', status: 'running' });
    const { store } = renderExecutionPanel();
    fireEvent.change(screen.getByTestId('purpose-textarea'), { target: { value: '불량 검출' } });
    await act(async () => { fireEvent.click(screen.getByTestId('start-btn')); });
    await waitFor(() => {
      expect(store.getState().execution.execution_id).toBe('exec-1');
    });
  });

  it('dispatches status "running" after successful start', async () => {
    mockStartExecution.mockResolvedValue({ execution_id: 'exec-1', status: 'running' });
    const { store } = renderExecutionPanel();
    fireEvent.change(screen.getByTestId('purpose-textarea'), { target: { value: '불량 검출' } });
    await act(async () => { fireEvent.click(screen.getByTestId('start-btn')); });
    await waitFor(() => {
      expect(store.getState().execution.status).toBe('running');
    });
  });

  it('start-btn is disabled when status is running', () => {
    renderExecutionPanel(RUNNING_EXECUTION_STATE);
    expect(screen.getByTestId('start-btn')).toBeDisabled();
  });

  it('shows start-error when startExecution API fails (execution_id stays null)', async () => {
    mockStartExecution.mockRejectedValue(Object.assign(new Error('images not uploaded'), { response: { status: 400 } }));
    renderExecutionPanel();
    fireEvent.change(screen.getByTestId('purpose-textarea'), { target: { value: '불량 검출' } });
    await act(async () => { fireEvent.click(screen.getByTestId('start-btn')); });
    await waitFor(() => {
      expect(screen.getByTestId('start-error')).toBeInTheDocument();
    });
  });
});

// ── Cancel execution ───────────────────────────────────────────

describe('ExecutionPanel — cancel execution', () => {
  it('cancel-btn is not rendered when status is idle', () => {
    renderExecutionPanel();
    expect(screen.queryByTestId('cancel-btn')).not.toBeInTheDocument();
  });

  it('cancel-btn is rendered when status is running', () => {
    renderExecutionPanel(RUNNING_EXECUTION_STATE);
    expect(screen.getByTestId('cancel-btn')).toBeInTheDocument();
  });

  it('calls cancelExecution with execution_id', async () => {
    mockCancelExecution.mockResolvedValue({ cancelled: true });
    renderExecutionPanel(RUNNING_EXECUTION_STATE);
    await act(async () => { fireEvent.click(screen.getByTestId('cancel-btn')); });
    expect(mockCancelExecution).toHaveBeenCalledWith('exec-1');
  });

  it('dispatches status "failed" after cancel', async () => {
    mockCancelExecution.mockResolvedValue({ cancelled: true });
    const { store } = renderExecutionPanel(RUNNING_EXECUTION_STATE);
    await act(async () => { fireEvent.click(screen.getByTestId('cancel-btn')); });
    await waitFor(() => {
      expect(store.getState().execution.status).toBe('failed');
    });
  });
});

// ── Status display ─────────────────────────────────────────────

describe('ExecutionPanel — status display', () => {
  it('shows status-badge when execution is running', () => {
    renderExecutionPanel({ ...RUNNING_EXECUTION_STATE, current_agent: 'orchestrator', current_iteration: 2 });
    expect(screen.getByTestId('status-badge')).toBeInTheDocument();
  });

  it('shows current-agent name when running', () => {
    renderExecutionPanel({ ...RUNNING_EXECUTION_STATE, current_agent: 'orchestrator', current_iteration: 2 });
    expect(screen.getByTestId('current-agent').textContent).toContain('orchestrator');
  });

  it('shows current-iteration number when running', () => {
    renderExecutionPanel({ ...RUNNING_EXECUTION_STATE, current_agent: null, current_iteration: 3 });
    expect(screen.getByTestId('current-iteration').textContent).toContain('3');
  });
});

// ── Result / error display ─────────────────────────────────────

describe('ExecutionPanel — result/error display', () => {
  it('shows success-message when status is success', () => {
    renderExecutionPanel({
      status: 'success',
      execution_id: 'exec-1',
      current_agent: null,
      current_iteration: 5,
      goal_validation: [],
      progress: 0,
    });
    expect(screen.getByTestId('success-message')).toBeInTheDocument();
  });

  it('shows error-message when status is failed', () => {
    renderExecutionPanel({
      status: 'failed',
      execution_id: 'exec-1',
      current_agent: null,
      current_iteration: 2,
      goal_validation: [],
      progress: 0,
    });
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
  });
});

// ── Polling ────────────────────────────────────────────────────

describe('ExecutionPanel — polling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls getExecutionStatus every 2 seconds when running', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      execution_id: 'exec-1',
      status: 'running',
      current_agent: 'spec',
      current_iteration: 1,
      result: null,
      error: null,
      started_at: '2026-05-04T00:00:00',
      completed_at: null,
    });

    renderExecutionPanel(RUNNING_EXECUTION_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(mockGetExecutionStatus).toHaveBeenCalledWith('exec-1');
  });

  it('updates current_agent and current_iteration in Redux from poll result', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      execution_id: 'exec-1',
      status: 'running',
      current_agent: 'spec_agent',
      current_iteration: 2,
      result: null,
      error: null,
      started_at: '2026-05-04T00:00:00',
      completed_at: null,
    });

    const { store } = renderExecutionPanel(RUNNING_EXECUTION_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().execution.current_agent).toBe('spec_agent');
    expect(store.getState().execution.current_iteration).toBe(2);
  });

  it('stops polling after status becomes success', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      execution_id: 'exec-1',
      status: 'success',
      current_agent: null,
      current_iteration: 5,
      result: {},
      error: null,
      started_at: '2026-05-04T00:00:00',
      completed_at: '2026-05-04T00:05:00',
    });

    renderExecutionPanel(RUNNING_EXECUTION_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    const countAfterFirst = mockGetExecutionStatus.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(4000);
      await Promise.resolve();
    });

    expect(mockGetExecutionStatus.mock.calls.length).toBe(countAfterFirst);
  });
});
