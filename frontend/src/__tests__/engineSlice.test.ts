import { describe, it, expect } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import engineReducer, {
  setEngineMode,
  setColabUrl,
  setConnectionStatus,
  setRemoteInfo,
  setEngineError,
  resetEngine,
  selectEngine,
} from '../store/slices/engineSlice';

// ── Initial state ──────────────────────────────────────────────

describe('engineSlice — initial state', () => {
  it('engine_mode defaults to local', () => {
    const state = engineReducer(undefined, { type: '@@INIT' });
    expect(state.engine_mode).toBe('local');
  });

  it('colab_url defaults to null', () => {
    const state = engineReducer(undefined, { type: '@@INIT' });
    expect(state.colab_url).toBeNull();
  });

  it('connection_status defaults to disconnected', () => {
    const state = engineReducer(undefined, { type: '@@INIT' });
    expect(state.connection_status).toBe('disconnected');
  });

  it('remote_info defaults to null', () => {
    const state = engineReducer(undefined, { type: '@@INIT' });
    expect(state.remote_info).toBeNull();
  });

  it('error defaults to null', () => {
    const state = engineReducer(undefined, { type: '@@INIT' });
    expect(state.error).toBeNull();
  });
});

// ── Actions ────────────────────────────────────────────────────

describe('engineSlice — setEngineMode', () => {
  it('updates engine_mode to colab', () => {
    const s = engineReducer(undefined, setEngineMode('colab'));
    expect(s.engine_mode).toBe('colab');
  });

  it('updates engine_mode back to local', () => {
    const s1 = engineReducer(undefined, setEngineMode('colab'));
    const s2 = engineReducer(s1, setEngineMode('local'));
    expect(s2.engine_mode).toBe('local');
  });
});

describe('engineSlice — setColabUrl', () => {
  it('updates colab_url with a URL string', () => {
    const s = engineReducer(undefined, setColabUrl('https://xxx.trycloudflare.com'));
    expect(s.colab_url).toBe('https://xxx.trycloudflare.com');
  });

  it('sets colab_url to null', () => {
    const s1 = engineReducer(undefined, setColabUrl('https://example.com'));
    const s2 = engineReducer(s1, setColabUrl(null));
    expect(s2.colab_url).toBeNull();
  });
});

describe('engineSlice — setConnectionStatus', () => {
  it('updates to connecting', () => {
    const s = engineReducer(undefined, setConnectionStatus('connecting'));
    expect(s.connection_status).toBe('connecting');
  });

  it('updates to connected', () => {
    const s = engineReducer(undefined, setConnectionStatus('connected'));
    expect(s.connection_status).toBe('connected');
  });

  it('updates to error', () => {
    const s = engineReducer(undefined, setConnectionStatus('error'));
    expect(s.connection_status).toBe('error');
  });

  it('updates back to disconnected', () => {
    const s1 = engineReducer(undefined, setConnectionStatus('connected'));
    const s2 = engineReducer(s1, setConnectionStatus('disconnected'));
    expect(s2.connection_status).toBe('disconnected');
  });
});

describe('engineSlice — setRemoteInfo', () => {
  it('updates remote_info with model_name', () => {
    const info = { model_name: 'gemma4:e4b', gpu_info: 'T4 16GB' };
    const s = engineReducer(undefined, setRemoteInfo(info));
    expect(s.remote_info).toEqual(info);
  });

  it('sets remote_info to null', () => {
    const s1 = engineReducer(undefined, setRemoteInfo({ model_name: 'gemma4:e4b' }));
    const s2 = engineReducer(s1, setRemoteInfo(null));
    expect(s2.remote_info).toBeNull();
  });

  it('stores only model_name when gpu_info is omitted', () => {
    const s = engineReducer(undefined, setRemoteInfo({ model_name: 'gemma4:27b' }));
    expect(s.remote_info?.model_name).toBe('gemma4:27b');
    expect(s.remote_info?.gpu_info).toBeUndefined();
  });
});

describe('engineSlice — setEngineError', () => {
  it('updates error string', () => {
    const s = engineReducer(undefined, setEngineError('Connection refused'));
    expect(s.error).toBe('Connection refused');
  });

  it('clears error by setting null', () => {
    const s1 = engineReducer(undefined, setEngineError('some error'));
    const s2 = engineReducer(s1, setEngineError(null));
    expect(s2.error).toBeNull();
  });
});

describe('engineSlice — resetEngine', () => {
  it('restores initial engine_mode', () => {
    const s1 = engineReducer(undefined, setEngineMode('colab'));
    const s2 = engineReducer(s1, resetEngine());
    expect(s2.engine_mode).toBe('local');
  });

  it('restores initial connection_status', () => {
    const s1 = engineReducer(undefined, setConnectionStatus('connected'));
    const s2 = engineReducer(s1, resetEngine());
    expect(s2.connection_status).toBe('disconnected');
  });

  it('clears colab_url', () => {
    const s1 = engineReducer(undefined, setColabUrl('https://example.com'));
    const s2 = engineReducer(s1, resetEngine());
    expect(s2.colab_url).toBeNull();
  });

  it('clears remote_info', () => {
    const s1 = engineReducer(undefined, setRemoteInfo({ model_name: 'gemma4:e4b' }));
    const s2 = engineReducer(s1, resetEngine());
    expect(s2.remote_info).toBeNull();
  });

  it('clears error', () => {
    const s1 = engineReducer(undefined, setEngineError('some error'));
    const s2 = engineReducer(s1, resetEngine());
    expect(s2.error).toBeNull();
  });
});

// ── Selector ───────────────────────────────────────────────────

describe('engineSlice — selectEngine', () => {
  it('returns the engine slice from state', () => {
    const store = configureStore({ reducer: { engine: engineReducer } });
    const state = store.getState();
    expect(selectEngine(state as any)).toEqual(state.engine);
  });

  it('reflects dispatched action in selector result', () => {
    const store = configureStore({ reducer: { engine: engineReducer } });
    store.dispatch(setEngineMode('colab'));
    expect(selectEngine(store.getState() as any).engine_mode).toBe('colab');
  });
});
