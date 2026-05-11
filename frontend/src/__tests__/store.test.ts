import { describe, it, expect } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import { renderHook } from '@testing-library/react';
import React from 'react';
import { Provider } from 'react-redux';

// Slice imports (don't exist yet)
import projectReducer, {
  setProjectName,
  resetProject,
  selectProject,
} from '../store/slices/projectSlice';
import imagesReducer, {
  addImage,
  removeImage,
  clearImagesByPurpose,
  resetImages,
  selectImages,
  selectAnalysisImages,
  selectTestImages,
} from '../store/slices/imagesSlice';
import configReducer, {
  setMode,
  setMaxIteration,
  setSuccessCriteria,
  resetConfig,
  selectConfig,
} from '../store/slices/configSlice';
import directivesReducer, {
  setDirective,
  setAllDirectives,
  resetDirectives,
  selectDirectives,
} from '../store/slices/directivesSlice';
import executionReducer, {
  setExecutionStatus,
  setCurrentAgent,
  setCurrentIteration,
  addGoalValidation,
  setProgress,
  resetExecution,
  selectExecution,
} from '../store/slices/executionSlice';
import resultReducer, {
  setResult,
  updateResult,
  resetResult,
  selectResult,
} from '../store/slices/resultSlice';
import logsReducer, {
  addLogEntry,
  clearLogs,
  selectLogs,
} from '../store/slices/logsSlice';

import { store, type RootState, type AppDispatch } from '../store';
import { useAppSelector, useAppDispatch } from '../store/hooks';

// ────────────────────────────────────────────────
// Store shape
// ────────────────────────────────────────────────

describe('store — shape', () => {
  it('has all 7 slice keys', () => {
    const state = store.getState();
    expect(state).toHaveProperty('project');
    expect(state).toHaveProperty('images');
    expect(state).toHaveProperty('config');
    expect(state).toHaveProperty('directives');
    expect(state).toHaveProperty('execution');
    expect(state).toHaveProperty('result');
    expect(state).toHaveProperty('logs');
  });
});

// ────────────────────────────────────────────────
// projectSlice
// ────────────────────────────────────────────────

describe('projectSlice', () => {
  const initialState = { name: '', created_at: null };

  it('has correct initial state', () => {
    const state = store.getState().project;
    expect(state).toEqual(initialState);
  });

  it('setProjectName updates name', () => {
    const s = projectReducer(undefined, setProjectName('MyProject'));
    expect(s.name).toBe('MyProject');
  });

  it('resetProject restores initial state', () => {
    const after = projectReducer({ name: 'X', created_at: '2026-01-01' }, resetProject());
    expect(after).toEqual(initialState);
  });

  it('selectProject returns project slice', () => {
    const state = store.getState();
    expect(selectProject(state)).toEqual(state.project);
  });
});

// ────────────────────────────────────────────────
// imagesSlice
// ────────────────────────────────────────────────

describe('imagesSlice', () => {
  const img = {
    id: '1',
    filename: 'a.png',
    purpose: 'analysis' as const,
    label: 'OK' as const,
    uploaded_at: '2026-01-01',
    path: '/tmp/a.png',
  };

  it('has correct initial state', () => {
    const state = store.getState().images;
    expect(state).toEqual({ analysis: [], test: [] });
  });

  it('addImage adds to analysis array', () => {
    const s = imagesReducer(undefined, addImage(img));
    expect(s.analysis).toHaveLength(1);
    expect(s.analysis[0]).toEqual(img);
  });

  it('addImage adds to test array when purpose is test', () => {
    const testImg = { ...img, id: '2', purpose: 'test' as const };
    const s = imagesReducer(undefined, addImage(testImg));
    expect(s.test).toHaveLength(1);
  });

  it('removeImage removes by id from correct array', () => {
    const s1 = imagesReducer(undefined, addImage(img));
    const s2 = imagesReducer(s1, removeImage({ id: '1', purpose: 'analysis' }));
    expect(s2.analysis).toHaveLength(0);
  });

  it('clearImagesByPurpose clears only that purpose', () => {
    const img2 = { ...img, id: '2', purpose: 'test' as const };
    let s = imagesReducer(undefined, addImage(img));
    s = imagesReducer(s, addImage(img2));
    s = imagesReducer(s, clearImagesByPurpose('analysis'));
    expect(s.analysis).toHaveLength(0);
    expect(s.test).toHaveLength(1);
  });

  it('resetImages restores initial state', () => {
    let s = imagesReducer(undefined, addImage(img));
    s = imagesReducer(s, resetImages());
    expect(s).toEqual({ analysis: [], test: [] });
  });

  it('selectAnalysisImages returns analysis array', () => {
    const state = store.getState();
    expect(selectAnalysisImages(state)).toEqual(state.images.analysis);
  });

  it('selectTestImages returns test array', () => {
    const state = store.getState();
    expect(selectTestImages(state)).toEqual(state.images.test);
  });
});

// ────────────────────────────────────────────────
// configSlice
// ────────────────────────────────────────────────

describe('configSlice', () => {
  it('has correct initial state', () => {
    const state = store.getState().config;
    expect(state.mode).toBe('inspection');
    expect(state.max_iteration).toBe(10);
    expect(state.success_criteria).toHaveProperty('accuracy');
  });

  it('setMode toggles to align', () => {
    const s = configReducer(undefined, setMode('align'));
    expect(s.mode).toBe('align');
  });

  it('setMode toggles back to inspection', () => {
    const s1 = configReducer(undefined, setMode('align'));
    const s2 = configReducer(s1, setMode('inspection'));
    expect(s2.mode).toBe('inspection');
  });

  it('setMaxIteration updates max_iteration', () => {
    const s = configReducer(undefined, setMaxIteration(20));
    expect(s.max_iteration).toBe(20);
  });

  it('setSuccessCriteria updates success_criteria', () => {
    const criteria = { coord_error: 0.5, success_rate: 0.95 };
    const s = configReducer(undefined, setSuccessCriteria(criteria));
    expect(s.success_criteria).toEqual(criteria);
  });

  it('resetConfig restores initial state', () => {
    const s1 = configReducer(undefined, setMode('align'));
    const s2 = configReducer(s1, resetConfig());
    expect(s2.mode).toBe('inspection');
  });

  it('selectConfig returns config slice', () => {
    const state = store.getState();
    expect(selectConfig(state)).toEqual(state.config);
  });
});

// ────────────────────────────────────────────────
// directivesSlice
// ────────────────────────────────────────────────

describe('directivesSlice', () => {
  it('has all directive fields null initially', () => {
    const state = store.getState().directives;
    const keys = ['orchestrator', 'spec', 'image_analysis', 'pipeline_composer',
      'vision_judge', 'inspection_plan', 'algorithm_coder', 'test'];
    keys.forEach(k => expect(state[k as keyof typeof state]).toBeNull());
  });

  it('setDirective updates a single directive', () => {
    const s = directivesReducer(undefined, setDirective({ key: 'orchestrator', value: 'do X' }));
    expect(s.orchestrator).toBe('do X');
    expect(s.spec).toBeNull();
  });

  it('setAllDirectives replaces all directives', () => {
    const all = {
      orchestrator: 'o', spec: 's', image_analysis: 'ia',
      pipeline_composer: 'pc', vision_judge: 'vj',
      inspection_plan: 'ip', algorithm_coder: 'ac', test: 't',
    };
    const s = directivesReducer(undefined, setAllDirectives(all));
    expect(s.orchestrator).toBe('o');
    expect(s.test).toBe('t');
  });

  it('resetDirectives sets all back to null', () => {
    const s1 = directivesReducer(undefined, setDirective({ key: 'orchestrator', value: 'x' }));
    const s2 = directivesReducer(s1, resetDirectives());
    expect(s2.orchestrator).toBeNull();
  });

  it('selectDirectives returns directives slice', () => {
    const state = store.getState();
    expect(selectDirectives(state)).toEqual(state.directives);
  });
});

// ────────────────────────────────────────────────
// executionSlice
// ────────────────────────────────────────────────

describe('executionSlice', () => {
  it('has correct initial state', () => {
    const state = store.getState().execution;
    expect(state.status).toBe('idle');
    expect(state.execution_id).toBeNull();
    expect(state.current_agent).toBeNull();
    expect(state.current_iteration).toBe(0);
    expect(state.goal_validation).toEqual([]);
    expect(state.progress).toBe(0);
  });

  it('status transitions idle → running', () => {
    const s = executionReducer(undefined, setExecutionStatus('running'));
    expect(s.status).toBe('running');
  });

  it('status transitions running → success', () => {
    const s1 = executionReducer(undefined, setExecutionStatus('running'));
    const s2 = executionReducer(s1, setExecutionStatus('success'));
    expect(s2.status).toBe('success');
  });

  it('status transitions running → failed', () => {
    const s1 = executionReducer(undefined, setExecutionStatus('running'));
    const s2 = executionReducer(s1, setExecutionStatus('failed'));
    expect(s2.status).toBe('failed');
  });

  it('setCurrentAgent updates current_agent', () => {
    const s = executionReducer(undefined, setCurrentAgent('orchestrator'));
    expect(s.current_agent).toBe('orchestrator');
  });

  it('setCurrentIteration updates current_iteration', () => {
    const s = executionReducer(undefined, setCurrentIteration(3));
    expect(s.current_iteration).toBe(3);
  });

  it('addGoalValidation appends to goal_validation', () => {
    const s1 = executionReducer(undefined, addGoalValidation('passed'));
    const s2 = executionReducer(s1, addGoalValidation('failed'));
    expect(s2.goal_validation).toEqual(['passed', 'failed']);
  });

  it('setProgress updates progress', () => {
    const s = executionReducer(undefined, setProgress(75));
    expect(s.progress).toBe(75);
  });

  it('resetExecution restores initial state', () => {
    const s1 = executionReducer(undefined, setExecutionStatus('running'));
    const s2 = executionReducer(s1, resetExecution());
    expect(s2.status).toBe('idle');
    expect(s2.progress).toBe(0);
  });

  it('selectExecution returns execution slice', () => {
    const state = store.getState();
    expect(selectExecution(state)).toEqual(state.execution);
  });
});

// ────────────────────────────────────────────────
// resultSlice
// ────────────────────────────────────────────────

describe('resultSlice', () => {
  it('has all fields null/empty initially', () => {
    const state = store.getState().result;
    expect(state.summary).toBeNull();
    expect(state.pipeline).toBeNull();
    expect(state.algorithm_code).toBeNull();
    expect(state.item_results).toBeNull();
    expect(state.improvement_suggestions).toBeNull();
    expect(state.decision).toBeNull();
  });

  it('setResult replaces full result', () => {
    const payload = {
      summary: 'done',
      pipeline: { steps: [] },
      inspection_plan: null,
      algorithm_code: 'code',
      algorithm_explanation: 'explain',
      metrics: { acc: 0.99 },
      item_results: [],
      improvement_suggestions: ['improve A'],
      decision: 'pass',
      decision_reason: 'good',
    };
    const s = resultReducer(undefined, setResult(payload));
    expect(s.summary).toBe('done');
    expect(s.decision).toBe('pass');
  });

  it('updateResult partially updates result', () => {
    const s1 = resultReducer(undefined, setResult({
      summary: 'initial',
      pipeline: null,
      inspection_plan: null,
      algorithm_code: null,
      algorithm_explanation: null,
      metrics: null,
      item_results: null,
      improvement_suggestions: null,
      decision: null,
      decision_reason: null,
    }));
    const s2 = resultReducer(s1, updateResult({ summary: 'updated' }));
    expect(s2.summary).toBe('updated');
    expect(s2.pipeline).toBeNull();
  });

  it('resetResult restores all null', () => {
    const s1 = resultReducer(undefined, setResult({
      summary: 'x', pipeline: null, inspection_plan: null,
      algorithm_code: null, algorithm_explanation: null,
      metrics: null, item_results: null, improvement_suggestions: null,
      decision: null, decision_reason: null,
    }));
    const s2 = resultReducer(s1, resetResult());
    expect(s2.summary).toBeNull();
  });

  it('selectResult returns result slice', () => {
    const state = store.getState();
    expect(selectResult(state)).toEqual(state.result);
  });
});

// ────────────────────────────────────────────────
// logsSlice
// ────────────────────────────────────────────────

describe('logsSlice', () => {
  const entry = {
    timestamp: '2026-01-01T00:00:00Z',
    agent: 'orchestrator',
    level: 'INFO' as const,
    message: 'started',
  };

  it('has empty entries initially', () => {
    const state = store.getState().logs;
    expect(state.entries).toEqual([]);
  });

  it('addLogEntry appends an entry', () => {
    const s = logsReducer(undefined, addLogEntry(entry));
    expect(s.entries).toHaveLength(1);
    expect(s.entries[0]).toEqual(entry);
  });

  it('addLogEntry appends multiple entries in order', () => {
    const entry2 = { ...entry, message: 'second' };
    let s = logsReducer(undefined, addLogEntry(entry));
    s = logsReducer(s, addLogEntry(entry2));
    expect(s.entries).toHaveLength(2);
    expect(s.entries[1].message).toBe('second');
  });

  it('clearLogs empties entries', () => {
    const s1 = logsReducer(undefined, addLogEntry(entry));
    const s2 = logsReducer(s1, clearLogs());
    expect(s2.entries).toHaveLength(0);
  });

  it('selectLogs returns logs slice', () => {
    const state = store.getState();
    expect(selectLogs(state)).toEqual(state.logs);
  });
});

// ────────────────────────────────────────────────
// Provider + typed hooks integration
// ────────────────────────────────────────────────

describe('typed hooks integration', () => {
  it('useAppSelector reads from store via Provider', () => {
    const testStore = configureStore({
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

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(Provider, { store: testStore }, children);

    const { result } = renderHook(
      () => useAppSelector((state: RootState) => state.project),
      { wrapper }
    );

    expect(result.current.name).toBe('');
    expect(result.current.created_at).toBeNull();
  });

  it('useAppDispatch dispatches actions through Provider', () => {
    const testStore = configureStore({
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

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(Provider, { store: testStore }, children);

    const { result } = renderHook(() => useAppDispatch(), { wrapper });
    result.current(setProjectName('TestProject'));

    expect(testStore.getState().project.name).toBe('TestProject');
  });
});
