import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

export interface InspectionCriteria {
  accuracy: number;
  fp_rate: number;
  fn_rate: number;
}

export interface AlignCriteria {
  coord_error: number;
  success_rate: number;
}

interface ConfigState {
  mode: 'inspection' | 'align';
  max_iteration: number;
  success_criteria: InspectionCriteria | AlignCriteria;
}

const initialState: ConfigState = {
  mode: 'inspection',
  max_iteration: 10,
  success_criteria: { accuracy: 0.95, fp_rate: 0.05, fn_rate: 0.05 },
};

const configSlice = createSlice({
  name: 'config',
  initialState,
  reducers: {
    setMode(state, action: PayloadAction<'inspection' | 'align'>) {
      state.mode = action.payload;
    },
    setMaxIteration(state, action: PayloadAction<number>) {
      state.max_iteration = action.payload;
    },
    setSuccessCriteria(state, action: PayloadAction<InspectionCriteria | AlignCriteria>) {
      state.success_criteria = action.payload;
    },
    resetConfig() {
      return initialState;
    },
  },
});

export const { setMode, setMaxIteration, setSuccessCriteria, resetConfig } = configSlice.actions;
export const selectConfig = (state: RootState) => state.config;
export default configSlice.reducer;
