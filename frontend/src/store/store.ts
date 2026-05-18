import { configureStore } from '@reduxjs/toolkit';
import copilotReducer from './slices/copilotSlice';
import ingestionReducer from './slices/ingestionSlice';

export const store = configureStore({
  reducer: {
    copilot: copilotReducer,
    ingestion: ingestionReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
