import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

interface ExecutionState {
  status: 'idle' | 'running' | 'success' | 'failed';
  execution_id: string | null;
  current_agent: string | null;
  current_iteration: number;
  goal_validation: string[];
  progress: number;
}

const initialState: ExecutionState = {
  status: 'idle',
  execution_id: null,
  current_agent: null,
  current_iteration: 0,
  goal_validation: [],
  progress: 0,
};

const executionSlice = createSlice({
  name: 'execution',
  initialState,
  reducers: {
    setExecutionStatus(state, action: PayloadAction<ExecutionState['status']>) {
      state.status = action.payload;
    },
    setExecutionId(state, action: PayloadAction<string | null>) {
      state.execution_id = action.payload;
    },
    setCurrentAgent(state, action: PayloadAction<string | null>) {
      state.current_agent = action.payload;
    },
    setCurrentIteration(state, action: PayloadAction<number>) {
      state.current_iteration = action.payload;
    },
    addGoalValidation(state, action: PayloadAction<string>) {
      state.goal_validation.push(action.payload);
    },
    setProgress(state, action: PayloadAction<number>) {
      state.progress = action.payload;
    },
    resetExecution() {
      return initialState;
    },
  },
});

export const {
  setExecutionStatus,
  setExecutionId,
  setCurrentAgent,
  setCurrentIteration,
  addGoalValidation,
  setProgress,
  resetExecution,
} = executionSlice.actions;
export const selectExecution = (state: RootState) => state.execution;
export default executionSlice.reducer;
