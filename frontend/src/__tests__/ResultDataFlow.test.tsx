import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act } from '@testing-library/react';
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

const { mockGetExecutionStatus } = vi.hoisted(() => ({
  mockGetExecutionStatus: vi.fn(),
}));

vi.mock('../services/api', () => ({
  startExecution: vi.fn(),
  getExecutionStatus: mockGetExecutionStatus,
  cancelExecution: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

const MOCK_RESULT = {
  summary: '검사 알고리즘 생성 완료: 정확도 98.5%',
  pipeline: {
    blocks: [
      { name: 'GaussianBlur', category: 'filter', params: { ksize: 5 } },
      { name: 'Threshold', category: 'threshold', params: { thresh: 127 } },
    ],
  },
  inspection_plan: [{ step: 1, description: '에지 검출' }],
  algorithm_code: 'import cv2\nimg = cv2.imread("test.png")',
  algorithm_explanation: '가우시안 블러를 사용하여 노이즈를 제거합니다.',
  metrics: { accuracy: 0.985, fp_rate: 0.01, fn_rate: 0.015 },
  item_results: [
    {
      item_name: 'OK_1.png',
      passed: true,
      metrics: { accuracy: 0.99, fp_rate: 0.01, fn_rate: 0.01 },
    },
    {
      item_name: 'NG_1.png',
      passed: false,
      metrics: { accuracy: 0.8, fp_rate: 0.1, fn_rate: 0.2 },
    },
  ],
  improvement_suggestions: ['조명 균일화 권장', '해상도 향상 고려'],
  decision: 'RULE_BASED',
  decision_reason: '단순 임계값 처리로 충분한 정확도 달성',
};

const SUCCESS_POLL_RESPONSE = {
  execution_id: 'exec-1',
  status: 'success',
  current_agent: null,
  current_iteration: 3,
  result: MOCK_RESULT,
  error: null,
  started_at: '2026-05-12T00:00:00Z',
  completed_at: '2026-05-12T00:05:00Z',
};

const FAILED_POLL_RESPONSE = {
  execution_id: 'exec-1',
  status: 'failed',
  current_agent: null,
  current_iteration: 1,
  result: null,
  error: '오케스트레이터 실행 중 오류 발생',
  started_at: '2026-05-12T00:00:00Z',
  completed_at: '2026-05-12T00:01:00Z',
};

const RUNNING_STATE = {
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

const renderWithStore = (executionState?: any) => {
  const store = createTestStore(executionState ? { execution: executionState } : undefined);
  render(
    <Provider store={store}>
      <ExecutionPanel />
    </Provider>,
  );
  return store;
};

// ── setResult dispatched on success ───────────────────────────────

describe('ResultDataFlow — setResult dispatched when polling returns success', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('dispatches setResult when poll returns status success', async () => {
    mockGetExecutionStatus.mockResolvedValue(SUCCESS_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    const resultState = store.getState().result;
    expect(resultState.summary).toBe(MOCK_RESULT.summary);
  });

  it('maps algorithm_code from backend result to result slice', async () => {
    mockGetExecutionStatus.mockResolvedValue(SUCCESS_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.algorithm_code).toBe(MOCK_RESULT.algorithm_code);
  });

  it('maps pipeline from backend result to result slice', async () => {
    mockGetExecutionStatus.mockResolvedValue(SUCCESS_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.pipeline).toEqual(MOCK_RESULT.pipeline);
  });

  it('maps item_results from backend result to result slice', async () => {
    mockGetExecutionStatus.mockResolvedValue(SUCCESS_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.item_results).toHaveLength(2);
    expect(store.getState().result.item_results![0].item_name).toBe('OK_1.png');
  });

  it('maps decision and decision_reason from backend result', async () => {
    mockGetExecutionStatus.mockResolvedValue(SUCCESS_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.decision).toBe('RULE_BASED');
    expect(store.getState().result.decision_reason).toBe(MOCK_RESULT.decision_reason);
  });

  it('maps improvement_suggestions from backend result', async () => {
    mockGetExecutionStatus.mockResolvedValue(SUCCESS_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.improvement_suggestions).toEqual(MOCK_RESULT.improvement_suggestions);
  });
});

// ── result slice NOT updated on failure ───────────────────────────

describe('ResultDataFlow — result slice NOT updated when polling returns failed', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('does NOT update result slice when poll returns status failed', async () => {
    mockGetExecutionStatus.mockResolvedValue(FAILED_POLL_RESPONSE);
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.summary).toBeNull();
  });

  it('does NOT update result slice when poll returns status cancelled', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      ...FAILED_POLL_RESPONSE,
      status: 'cancelled',
    });
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.summary).toBeNull();
  });
});

// ── null-safe mapping ─────────────────────────────────────────────

describe('ResultDataFlow — null-safe result mapping', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it('handles null result fields gracefully (no crash)', async () => {
    mockGetExecutionStatus.mockResolvedValue({
      ...SUCCESS_POLL_RESPONSE,
      result: {
        summary: '완료',
        pipeline: null,
        inspection_plan: null,
        algorithm_code: null,
        algorithm_explanation: null,
        metrics: null,
        item_results: null,
        improvement_suggestions: null,
        decision: null,
        decision_reason: null,
      },
    });
    const store = renderWithStore(RUNNING_STATE);

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(store.getState().result.summary).toBe('완료');
    expect(store.getState().result.pipeline).toBeNull();
  });
});
