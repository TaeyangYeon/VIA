import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

interface ResultState {
  summary: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pipeline: any | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  inspection_plan: any | null;
  algorithm_code: string | null;
  algorithm_explanation: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metrics: any | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  item_results: any[] | null;
  improvement_suggestions: string[] | null;
  decision: string | null;
  decision_reason: string | null;
}

const initialState: ResultState = {
  summary: null,
  pipeline: null,
  inspection_plan: null,
  algorithm_code: null,
  algorithm_explanation: null,
  metrics: null,
  item_results: null,
  improvement_suggestions: null,
  decision: null,
  decision_reason: null,
};

const resultSlice = createSlice({
  name: 'result',
  initialState,
  reducers: {
    setResult(_state, action: PayloadAction<ResultState>) {
      return action.payload;
    },
    updateResult(state, action: PayloadAction<Partial<ResultState>>) {
      return { ...state, ...action.payload };
    },
    resetResult() {
      return initialState;
    },
  },
});

export const { setResult, updateResult, resetResult } = resultSlice.actions;
export const selectResult = (state: RootState) => state.result;
export default resultSlice.reducer;
