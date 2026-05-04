import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import DirectivePanel from '../components/panels/DirectivePanel';
import projectReducer from '../store/slices/projectSlice';
import imagesReducer from '../store/slices/imagesSlice';
import configReducer from '../store/slices/configSlice';
import directivesReducer from '../store/slices/directivesSlice';
import executionReducer from '../store/slices/executionSlice';
import resultReducer from '../store/slices/resultSlice';
import logsReducer from '../store/slices/logsSlice';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  getDirectives: vi.fn(),
  saveDirectives: vi.fn(),
  resetDirectives: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

const EMPTY_DIRECTIVES = {
  orchestrator: null,
  spec: null,
  image_analysis: null,
  pipeline_composer: null,
  vision_judge: null,
  inspection_plan: null,
  algorithm_coder: null,
  test: null,
};

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

const renderDirectivePanel = () => {
  const store = createTestStore();
  const result = render(
    <Provider store={store}>
      <DirectivePanel />
    </Provider>,
  );
  return { ...result, store };
};

// ── Rendering ──────────────────────────────────────────────────

describe('DirectivePanel — rendering', () => {
  beforeEach(() => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
  });

  it('renders 오케스트레이터 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
  });

  it('renders 스펙 에이전트 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('스펙 에이전트')).toBeInTheDocument());
  });

  it('renders 이미지 분석 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('이미지 분석')).toBeInTheDocument());
  });

  it('renders 파이프라인 구성 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('파이프라인 구성')).toBeInTheDocument());
  });

  it('renders 비전 판정 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('비전 판정')).toBeInTheDocument());
  });

  it('renders 검사 설계 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('검사 설계')).toBeInTheDocument());
  });

  it('renders 알고리즘 코더 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('알고리즘 코더')).toBeInTheDocument());
  });

  it('renders 테스트 에이전트 card', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('테스트 에이전트')).toBeInTheDocument());
  });

  it('renders Save All button', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByTestId('save-all-btn')).toBeInTheDocument());
  });

  it('renders Reset All button', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByTestId('reset-all-btn')).toBeInTheDocument());
  });
});

// ── Collapse / Expand ──────────────────────────────────────────

describe('DirectivePanel — collapse/expand', () => {
  beforeEach(() => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
  });

  it('textarea is hidden before any card is expanded', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    expect(screen.queryByTestId('textarea-orchestrator')).not.toBeInTheDocument();
  });

  it('clicking orchestrator card expands it and shows textarea', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    expect(screen.getByTestId('textarea-orchestrator')).toBeInTheDocument();
  });

  it('clicking expanded card again collapses it and hides textarea', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    expect(screen.queryByTestId('textarea-orchestrator')).not.toBeInTheDocument();
  });

  it('expanding second card collapses the first (accordion)', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    expect(screen.getByTestId('textarea-orchestrator')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('card-spec'));
    expect(screen.queryByTestId('textarea-orchestrator')).not.toBeInTheDocument();
    expect(screen.getByTestId('textarea-spec')).toBeInTheDocument();
  });
});

// ── Textarea placeholder ───────────────────────────────────────

describe('DirectivePanel — textarea', () => {
  beforeEach(() => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
  });

  it('textarea has placeholder text', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    const textarea = screen.getByTestId('textarea-orchestrator');
    expect(textarea).toHaveAttribute('placeholder', '에이전트가 자동으로 판단합니다...');
  });
});

// ── Directive input dispatches to store ────────────────────────

describe('DirectivePanel — directive input', () => {
  beforeEach(() => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
  });

  it('typing in textarea updates the Redux store directive', async () => {
    const { store } = renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    const textarea = screen.getByTestId('textarea-orchestrator');
    fireEvent.change(textarea, { target: { value: '정확도 최우선' } });
    fireEvent.blur(textarea);
    await waitFor(() => {
      expect(store.getState().directives.orchestrator).toBe('정확도 최우선');
    });
  });

  it('clearing textarea sets directive to null in store', async () => {
    vi.mocked(api.getDirectives).mockResolvedValueOnce({
      ...EMPTY_DIRECTIVES,
      orchestrator: '기존 지시문',
    });
    const { store } = renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('card-orchestrator'));
    const textarea = screen.getByTestId('textarea-orchestrator');
    fireEvent.change(textarea, { target: { value: '' } });
    fireEvent.blur(textarea);
    await waitFor(() => {
      expect(store.getState().directives.orchestrator).toBeNull();
    });
  });
});

// ── Directive indicator ────────────────────────────────────────

describe('DirectivePanel — directive indicator', () => {
  it('shows indicator dot when directive is set and card is collapsed', async () => {
    vi.mocked(api.getDirectives).mockResolvedValueOnce({
      ...EMPTY_DIRECTIVES,
      orchestrator: '일부 지시문',
    });
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    expect(screen.getByTestId('indicator-orchestrator')).toBeInTheDocument();
  });

  it('does not show indicator dot when directive is null and card is collapsed', async () => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    expect(screen.queryByTestId('indicator-orchestrator')).not.toBeInTheDocument();
  });
});

// ── Truncated preview ──────────────────────────────────────────

describe('DirectivePanel — truncated preview', () => {
  it('shows truncated preview of directive when card is collapsed', async () => {
    const longText = '이것은 매우 긴 지시문입니다. 50자를 초과하는 텍스트입니다. 잘려야 합니다.';
    vi.mocked(api.getDirectives).mockResolvedValueOnce({
      ...EMPTY_DIRECTIVES,
      orchestrator: longText,
    });
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    expect(screen.getByTestId('preview-orchestrator')).toBeInTheDocument();
    const previewEl = screen.getByTestId('preview-orchestrator');
    expect(previewEl.textContent!.length).toBeLessThanOrEqual(55);
  });

  it('shows short directive in full when shorter than 50 chars', async () => {
    const shortText = '짧은 지시문';
    vi.mocked(api.getDirectives).mockResolvedValueOnce({
      ...EMPTY_DIRECTIVES,
      orchestrator: shortText,
    });
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    const previewEl = screen.getByTestId('preview-orchestrator');
    expect(previewEl.textContent).toContain(shortText);
  });
});

// ── Save All ───────────────────────────────────────────────────

describe('DirectivePanel — Save All', () => {
  it('calls saveDirectives with current directives state', async () => {
    vi.mocked(api.getDirectives).mockResolvedValueOnce({
      ...EMPTY_DIRECTIVES,
      orchestrator: '테스트 지시문',
    });
    vi.mocked(api.saveDirectives).mockResolvedValue({
      directives: { ...EMPTY_DIRECTIVES, orchestrator: '테스트 지시문' },
    });
    const { store: _store } = renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-all-btn'));
    });
    await waitFor(() => {
      expect(api.saveDirectives).toHaveBeenCalledWith(
        expect.objectContaining({ orchestrator: '테스트 지시문' }),
      );
    });
  });

  it('shows success feedback after save', async () => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
    vi.mocked(api.saveDirectives).mockResolvedValue({ directives: { ...EMPTY_DIRECTIVES } });
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-all-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('save-success')).toBeInTheDocument();
    });
  });

  it('shows error state when saveDirectives API fails', async () => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
    vi.mocked(api.saveDirectives).mockRejectedValue(new Error('Network error'));
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('save-all-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('save-error')).toBeInTheDocument();
    });
  });
});

// ── Reset All ─────────────────────────────────────────────────

describe('DirectivePanel — Reset All', () => {
  it('calls resetDirectives API when Reset All is clicked', async () => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
    vi.mocked(api.resetDirectives).mockResolvedValue({ reset: true });
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('reset-all-btn'));
    });
    await waitFor(() => {
      expect(api.resetDirectives).toHaveBeenCalled();
    });
  });

  it('dispatches resetDirectives to store after reset', async () => {
    vi.mocked(api.getDirectives).mockResolvedValueOnce({
      ...EMPTY_DIRECTIVES,
      orchestrator: '기존 지시문',
    });
    vi.mocked(api.resetDirectives).mockResolvedValue({ reset: true });
    const { store } = renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('reset-all-btn'));
    });
    await waitFor(() => {
      expect(store.getState().directives.orchestrator).toBeNull();
    });
  });

  it('shows error state when resetDirectives API fails', async () => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
    vi.mocked(api.resetDirectives).mockRejectedValue(new Error('Reset failed'));
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    await act(async () => {
      fireEvent.click(screen.getByTestId('reset-all-btn'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('reset-error')).toBeInTheDocument();
    });
  });
});

// ── Loading state ─────────────────────────────────────────────

describe('DirectivePanel — loading state', () => {
  it('shows loading state while getDirectives is pending', async () => {
    let resolve!: (v: typeof EMPTY_DIRECTIVES) => void;
    vi.mocked(api.getDirectives).mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );
    renderDirectivePanel();
    expect(screen.getByTestId('directives-loading')).toBeInTheDocument();
    await act(async () => {
      resolve({ ...EMPTY_DIRECTIVES });
    });
    await waitFor(() => {
      expect(screen.queryByTestId('directives-loading')).not.toBeInTheDocument();
    });
  });
});

// ── Initial load / getDirectives on mount ──────────────────────

describe('DirectivePanel — initial load', () => {
  it('calls getDirectives on mount', async () => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
    renderDirectivePanel();
    await waitFor(() => {
      expect(api.getDirectives).toHaveBeenCalledTimes(1);
    });
  });

  it('dispatches setAllDirectives with backend data on mount', async () => {
    const backendData = { ...EMPTY_DIRECTIVES, orchestrator: '백엔드 지시문' };
    vi.mocked(api.getDirectives).mockResolvedValue(backendData);
    const { store } = renderDirectivePanel();
    await waitFor(() => {
      expect(store.getState().directives.orchestrator).toBe('백엔드 지시문');
    });
  });

  it('shows error state if getDirectives fails on mount', async () => {
    vi.mocked(api.getDirectives).mockRejectedValue(new Error('Load failed'));
    renderDirectivePanel();
    await waitFor(() => {
      expect(screen.getByTestId('load-error')).toBeInTheDocument();
    });
  });
});

// ── Empty state ────────────────────────────────────────────────

describe('DirectivePanel — empty state', () => {
  beforeEach(() => {
    vi.mocked(api.getDirectives).mockResolvedValue({ ...EMPTY_DIRECTIVES });
  });

  it('shows no indicator dots when all directives are null', async () => {
    renderDirectivePanel();
    await waitFor(() => expect(screen.getByText('오케스트레이터')).toBeInTheDocument());
    const indicators = screen.queryAllByTestId(/^indicator-/);
    expect(indicators).toHaveLength(0);
  });

  it('shows empty state message when all directives are null', async () => {
    renderDirectivePanel();
    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });
});
