import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

export interface LogEntry {
  timestamp: string;
  agent: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  message: string;
}

interface LogsState {
  entries: LogEntry[];
}

const initialState: LogsState = {
  entries: [],
};

const logsSlice = createSlice({
  name: 'logs',
  initialState,
  reducers: {
    addLogEntry(state, action: PayloadAction<LogEntry>) {
      state.entries.push(action.payload);
    },
    clearLogs(state) {
      state.entries = [];
    },
  },
});

export const { addLogEntry, clearLogs } = logsSlice.actions;
export const selectLogs = (state: RootState) => state.logs;
export default logsSlice.reducer;
