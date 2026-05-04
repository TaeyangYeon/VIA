import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import ResultPanel from '../components/panels/ResultPanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';

afterEach(() => {
  vi.clearAllMocks();
});

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
    preloadedState,
  });

const renderResultPanel = (resultState?: any) => {
  const preloadedState = resultState !== undefined ? { result: resultState } : undefined;
  const store = createTestStore(preloadedState);
  const rendered = render(
    <Provider store={store}>
      <ResultPanel />
    </Provider>,
  );
  return { ...rendered, store };
};

const SAMPLE_ITEM_RESULTS = [
  {
    item_id: 1,
    item_name: 'item_001',
    passed: true,
    metrics: { accuracy: 0.98, fp_rate: 0.01, fn_rate: 0.01, coord_error: 0, success_rate: 1.0 },
    details: 'OK',
  },
  {
    item_id: 2,
    item_name: 'item_002',
    passed: false,
    metrics: { accuracy: 0.85, fp_rate: 0.10, fn_rate: 0.05, coord_error: 0, success_rate: 0.9 },
    details: 'Failed',
  },
];

const SAMPLE_PIPELINE = {
  pipeline_id: 'p1',
  name: 'Test Pipeline',
  blocks: [
    { name: 'GaussianBlur', category: 'noise_reduction', params: { ksize: 5 } },
    { name: 'Threshold', category: 'threshold', params: { value: 128 } },
  ],
  score: 0.95,
};

const SAMPLE_RESULT = {
  summary: '검사 완료: 정확도 97.5%',
  pipeline: SAMPLE_PIPELINE,
  inspection_plan: null,
  algorithm_code: 'import cv2\ndef process(img):\n    return img',
  algorithm_explanation: '가우시안 블러로 노이즈를 제거하고 임계값 처리를 적용합니다.',
  metrics: { accuracy: 0.975, fp_rate: 0.02, fn_rate: 0.005 },
  item_results: SAMPLE_ITEM_RESULTS,
  improvement_suggestions: ['더 강한 전처리 적용', '임계값 조정'],
  decision: 'RULE_BASED',
  decision_reason: '간단한 이진 분류에 적합합니다.',
};

// ── Empty state ────────────────────────────────────────────────

describe('ResultPanel — empty state', () => {
  it('shows empty-state when result has no summary (default store)', () => {
    renderResultPanel();
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('shows "실행 결과가 여기에 표시됩니다" in empty state', () => {
    renderResultPanel();
    expect(screen.getByTestId('empty-state').textContent).toContain('실행 결과가 여기에 표시됩니다');
  });

  it('does not show tabs in empty state', () => {
    renderResultPanel();
    expect(screen.queryByTestId('tab-code')).not.toBeInTheDocument();
  });
});

// ── Summary display ────────────────────────────────────────────

describe('ResultPanel — summary', () => {
  it('shows summary text when result data is present', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('summary-text').textContent).toContain('검사 완료');
  });

  it('does not show empty-state when summary is present', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument();
  });
});

// ── Code section ───────────────────────────────────────────────

describe('ResultPanel — code section', () => {
  it('renders code tab button', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('tab-code')).toBeInTheDocument();
  });

  it('shows code-block on Code tab (default active)', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('code-block')).toBeInTheDocument();
  });

  it('code-block contains algorithm_code text', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('code-block').textContent).toContain('import cv2');
  });

  it('shows algorithm-explanation text', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('algorithm-explanation').textContent).toContain('가우시안 블러');
  });
});

// ── Metrics section ────────────────────────────────────────────

describe('ResultPanel — metrics section', () => {
  it('renders metrics tab button', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('tab-metrics')).toBeInTheDocument();
  });

  it('clicking metrics tab shows metrics-section', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-metrics'));
    expect(screen.getByTestId('metrics-section')).toBeInTheDocument();
  });

  it('metrics-section shows item names from item_results', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-metrics'));
    expect(screen.getByTestId('metrics-section').textContent).toContain('item_001');
  });

  it('code-block not visible after switching to metrics tab', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-metrics'));
    expect(screen.queryByTestId('code-block')).not.toBeInTheDocument();
  });
});

// ── Pipeline section ───────────────────────────────────────────

describe('ResultPanel — pipeline section', () => {
  it('renders pipeline tab button', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('tab-pipeline')).toBeInTheDocument();
  });

  it('clicking pipeline tab shows pipeline-section', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-pipeline'));
    expect(screen.getByTestId('pipeline-section')).toBeInTheDocument();
  });

  it('pipeline-section shows block names from pipeline', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-pipeline'));
    expect(screen.getByTestId('pipeline-section').textContent).toContain('GaussianBlur');
  });
});

// ── Decision section ───────────────────────────────────────────

describe('ResultPanel — decision section', () => {
  it('renders decision tab button', () => {
    renderResultPanel(SAMPLE_RESULT);
    expect(screen.getByTestId('tab-decision')).toBeInTheDocument();
  });

  it('clicking decision tab shows decision-section', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-decision'));
    expect(screen.getByTestId('decision-section')).toBeInTheDocument();
  });

  it('shows decision-badge with RULE_BASED text', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-decision'));
    expect(screen.getByTestId('decision-badge').textContent).toContain('RULE_BASED');
  });

  it('shows decision-reason text', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-decision'));
    expect(screen.getByTestId('decision-reason').textContent).toContain('간단한 이진 분류');
  });

  it('shows improvement suggestions in suggestions-list', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-decision'));
    expect(screen.getByTestId('suggestions-list').textContent).toContain('더 강한 전처리 적용');
  });

  it('shows EDGE_LEARNING badge for EDGE_LEARNING decision', () => {
    renderResultPanel({ ...SAMPLE_RESULT, decision: 'EDGE_LEARNING' });
    fireEvent.click(screen.getByTestId('tab-decision'));
    expect(screen.getByTestId('decision-badge').textContent).toContain('EDGE_LEARNING');
  });

  it('shows DEEP_LEARNING badge for DEEP_LEARNING decision', () => {
    renderResultPanel({ ...SAMPLE_RESULT, decision: 'DEEP_LEARNING' });
    fireEvent.click(screen.getByTestId('tab-decision'));
    expect(screen.getByTestId('decision-badge').textContent).toContain('DEEP_LEARNING');
  });
});

// ── Tab switching ──────────────────────────────────────────────

describe('ResultPanel — tab switching', () => {
  it('can switch back to Code tab after switching to Metrics', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-metrics'));
    expect(screen.queryByTestId('code-block')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('tab-code'));
    expect(screen.getByTestId('code-block')).toBeInTheDocument();
  });

  it('can switch between all four tabs without error', () => {
    renderResultPanel(SAMPLE_RESULT);
    fireEvent.click(screen.getByTestId('tab-metrics'));
    fireEvent.click(screen.getByTestId('tab-pipeline'));
    fireEvent.click(screen.getByTestId('tab-decision'));
    fireEvent.click(screen.getByTestId('tab-code'));
    expect(screen.getByTestId('code-block')).toBeInTheDocument();
  });
});
