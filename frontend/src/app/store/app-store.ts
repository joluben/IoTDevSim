import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { STORAGE_KEYS } from '@/app/config/constants';

// Application-wide state interface
export interface AppState {
  // Application info
  isInitialized: boolean;
  version: string;
  
  // Loading states
  isLoading: boolean;
  loadingMessage: string;
  
  // Error handling
  error: string | null;
  
  // User preferences
  preferences: {
    language: string;
    timezone: string;
    dateFormat: string;
    numberFormat: string;
  };
  
  // Feature flags
  features: {
    enableAnalytics: boolean;
    enableWebSocket: boolean;
    enableBetaFeatures: boolean;
  };
}

// Application actions interface
export interface AppActions {
  // Initialization
  initialize: () => Promise<void>;
  setInitialized: (initialized: boolean) => void;
  
  // Loading management
  setLoading: (loading: boolean, message?: string) => void;
  
  // Error management
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Preferences management
  updatePreferences: (preferences: Partial<AppState['preferences']>) => void;
  resetPreferences: () => void;
  
  // Feature flags
  updateFeatures: (features: Partial<AppState['features']>) => void;
  
  // Reset store
  reset: () => void;
}

// Combined state and actions
export type AppStore = AppState & AppActions;

// Default state
const defaultState: AppState = {
  isInitialized: false,
  version: '2.0.0',
  isLoading: false,
  loadingMessage: '',
  error: null,
  preferences: {
    language: 'en',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    dateFormat: 'MM/dd/yyyy',
    numberFormat: 'en-US',
  },
  features: {
    enableAnalytics: false,
    enableWebSocket: true,
    enableBetaFeatures: false,
  },
};

// Create the store
export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...defaultState,

        // Initialization
        initialize: async () => {
          set((state) => {
            state.isLoading = true;
            state.loadingMessage = 'Initializing application...';
          });

          try {
            // Perform initialization tasks
            await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate async initialization
            
            set((state) => {
              state.isInitialized = true;
              state.isLoading = false;
              state.loadingMessage = '';
              state.error = null;
            });
          } catch (error) {
            set((state) => {
              state.isLoading = false;
              state.loadingMessage = '';
              state.error = error instanceof Error ? error.message : 'Initialization failed';
            });
          }
        },

        setInitialized: (initialized) => {
          set((state) => {
            state.isInitialized = initialized;
          });
        },

        // Loading management
        setLoading: (loading, message = '') => {
          set((state) => {
            state.isLoading = loading;
            state.loadingMessage = message;
          });
        },

        // Error management
        setError: (error) => {
          set((state) => {
            state.error = error;
          });
        },

        clearError: () => {
          set((state) => {
            state.error = null;
          });
        },

        // Preferences management
        updatePreferences: (newPreferences) => {
          set((state) => {
            state.preferences = { ...state.preferences, ...newPreferences };
          });
        },

        resetPreferences: () => {
          set((state) => {
            state.preferences = defaultState.preferences;
          });
        },

        // Feature flags
        updateFeatures: (newFeatures) => {
          set((state) => {
            state.features = { ...state.features, ...newFeatures };
          });
        },

        // Reset store
        reset: () => {
          set(defaultState);
        },
      })),
      {
        name: STORAGE_KEYS.userPreferences,
        partialize: (state) => ({
          preferences: state.preferences,
          features: state.features,
        }),
      }
    ),
    {
      name: 'app-store',
    }
  )
);
