import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

interface ProjectState {
  name: string;
  created_at: string | null;
}

const initialState: ProjectState = {
  name: '',
  created_at: null,
};

const projectSlice = createSlice({
  name: 'project',
  initialState,
  reducers: {
    setProjectName(state, action: PayloadAction<string>) {
      state.name = action.payload;
    },
    setCreatedAt(state, action: PayloadAction<string>) {
      state.created_at = action.payload;
    },
    resetProject() {
      return initialState;
    },
  },
});

export const { setProjectName, setCreatedAt, resetProject } = projectSlice.actions;
export const selectProject = (state: RootState) => state.project;
export default projectSlice.reducer;
