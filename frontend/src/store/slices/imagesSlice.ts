import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

export interface ImageMeta {
  id: string;
  filename: string;
  purpose: 'analysis' | 'test';
  label: 'OK' | 'NG';
  uploaded_at: string;
  path: string;
}

interface ImagesState {
  analysis: ImageMeta[];
  test: ImageMeta[];
}

const initialState: ImagesState = {
  analysis: [],
  test: [],
};

const imagesSlice = createSlice({
  name: 'images',
  initialState,
  reducers: {
    addImage(state, action: PayloadAction<ImageMeta>) {
      const img = action.payload;
      state[img.purpose].push(img);
    },
    removeImage(state, action: PayloadAction<{ id: string; purpose: 'analysis' | 'test' }>) {
      const { id, purpose } = action.payload;
      state[purpose] = state[purpose].filter(img => img.id !== id);
    },
    clearImagesByPurpose(state, action: PayloadAction<'analysis' | 'test'>) {
      state[action.payload] = [];
    },
    resetImages() {
      return initialState;
    },
  },
});

export const { addImage, removeImage, clearImagesByPurpose, resetImages } = imagesSlice.actions;
export const selectImages = (state: RootState) => state.images;
export const selectAnalysisImages = (state: RootState) => state.images.analysis;
export const selectTestImages = (state: RootState) => state.images.test;
export default imagesSlice.reducer;
