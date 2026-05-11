import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

interface RemoteInfo {
  model_name?: string;
  gpu_info?: string;
}

interface EngineState {
  engine_mode: 'local' | 'colab';
  colab_url: string | null;
  connection_status: 'disconnected' | 'connecting' | 'connected' | 'error';
  remote_info: RemoteInfo | null;
  error: string | null;
}

const initialState: EngineState = {
  engine_mode: 'local',
  colab_url: null,
  connection_status: 'disconnected',
  remote_info: null,
  error: null,
};

const engineSlice = createSlice({
  name: 'engine',
  initialState,
  reducers: {
    setEngineMode(state, action: PayloadAction<'local' | 'colab'>) {
      state.engine_mode = action.payload;
    },
    setColabUrl(state, action: PayloadAction<string | null>) {
      state.colab_url = action.payload;
    },
    setConnectionStatus(
      state,
      action: PayloadAction<'disconnected' | 'connecting' | 'connected' | 'error'>,
    ) {
      state.connection_status = action.payload;
    },
    setRemoteInfo(state, action: PayloadAction<RemoteInfo | null>) {
      state.remote_info = action.payload;
    },
    setEngineError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
    resetEngine() {
      return initialState;
    },
  },
});

export const {
  setEngineMode,
  setColabUrl,
  setConnectionStatus,
  setRemoteInfo,
  setEngineError,
  resetEngine,
} = engineSlice.actions;

export const selectEngine = (state: RootState) => state.engine;
export default engineSlice.reducer;
