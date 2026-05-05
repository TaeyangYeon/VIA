import { configureStore } from '@reduxjs/toolkit';
import projectReducer from './slices/projectSlice';
import imagesReducer from './slices/imagesSlice';
import configReducer from './slices/configSlice';
import directivesReducer from './slices/directivesSlice';
import executionReducer from './slices/executionSlice';
import resultReducer from './slices/resultSlice';
import logsReducer from './slices/logsSlice';
import engineReducer from './slices/engineSlice';

export const store = configureStore({
  reducer: {
    project: projectReducer,
    images: imagesReducer,
    config: configReducer,
    directives: directivesReducer,
    execution: executionReducer,
    result: resultReducer,
    logs: logsReducer,
    engine: engineReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
