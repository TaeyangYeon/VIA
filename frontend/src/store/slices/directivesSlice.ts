import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

interface DirectivesState {
  orchestrator: string | null;
  spec: string | null;
  image_analysis: string | null;
  pipeline_composer: string | null;
  vision_judge: string | null;
  inspection_plan: string | null;
  algorithm_coder: string | null;
  test: string | null;
}

const initialState: DirectivesState = {
  orchestrator: null,
  spec: null,
  image_analysis: null,
  pipeline_composer: null,
  vision_judge: null,
  inspection_plan: null,
  algorithm_coder: null,
  test: null,
};

const directivesSlice = createSlice({
  name: 'directives',
  initialState,
  reducers: {
    setDirective(
      state,
      action: PayloadAction<{ key: keyof DirectivesState; value: string | null }>
    ) {
      state[action.payload.key] = action.payload.value;
    },
    setAllDirectives(_state, action: PayloadAction<DirectivesState>) {
      return action.payload;
    },
    resetDirectives() {
      return initialState;
    },
  },
});

export const { setDirective, setAllDirectives, resetDirectives } = directivesSlice.actions;
export const selectDirectives = (state: RootState) => state.directives;
export default directivesSlice.reducer;
