import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { AUTH_CONFIG } from '@/app/config/constants';
import { authService, TokenStorage, type AuthResponse, type LoginRequest } from '@/services/auth.service';
import { apiClient } from '@/services/api.client';

// User interface
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  createdAt: string;
  lastLoginAt?: string;
}

// Authentication state interface
export interface AuthState {
  // Authentication status
  isAuthenticated: boolean;
  isLoading: boolean;
  
  // User data
  user: User | null;
  
  // Tokens
  token: string | null;
  refreshToken: string | null;
  tokenExpiration: number | null;
  
  // Session management
  sessionTimeout: number | null;
  lastActivity: number;
  isSessionActive: boolean;
  sessionTimeoutId: NodeJS.Timeout | null;
  
  // Error handling
  error: string | null;
}

// Authentication actions interface
export interface AuthActions {
  // Authentication
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  
  // Token management
  setTokens: (token: string, refreshToken: string, expiresIn: number) => void;
  refreshTokens: () => Promise<string>;
  clearTokens: () => void;
  
  // User management
  setUser: (user: User) => void;
  updateUser: (updates: Partial<User>) => void;
  clearUser: () => void;
  
  // Session management
  updateLastActivity: () => void;
  checkSession: () => boolean;
  startSessionTimeout: () => void;
  clearSessionTimeout: () => void;
  handleSessionTimeout: () => void;
  
  // Error management
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Utilities
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  
  // Reset store
  reset: () => void;
}

// Combined state and actions
export type AuthStore = AuthState & AuthActions;

// Default state
const defaultState: AuthState = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
  token: null,
  refreshToken: null,
  tokenExpiration: null,
  sessionTimeout: null,
  lastActivity: Date.now(),
  isSessionActive: true,
  sessionTimeoutId: null,
  error: null,
};

// Create the store
export const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...defaultState,

        // Authentication
        login: async (email, password) => {
          set((state) => {
            state.isLoading = true;
            state.error = null;
          });

          try {
            const credentials: LoginRequest = { email, password };
            const data: AuthResponse = await authService.login(credentials);
            
            // Store tokens via TokenStorage for apiClient access
            TokenStorage.setToken(data.token);
            TokenStorage.setRefreshToken(data.refreshToken);
            
            set((state) => {
              state.isAuthenticated = true;
              state.isLoading = false;
              state.user = data.user;
              state.token = data.token;
              state.refreshToken = data.refreshToken;
              state.tokenExpiration = Date.now() + data.expiresIn * 1000;
              state.lastActivity = Date.now();
              state.isSessionActive = true;
              state.error = null;
            });

            // Start session timeout monitoring
            get().startSessionTimeout();
            
            // Set up API client unauthorized callback
            apiClient.setUnauthorizedCallback(() => {
              get().logout();
            });
          } catch (error) {
            set((state) => {
              state.isLoading = false;
              state.error = error instanceof Error ? error.message : 'Login failed';
            });
            throw error;
          }
        },

        logout: async () => {
          // Clear session timeout
          get().clearSessionTimeout();
          
          try {
            // Notify server about logout
            await authService.logout();
          } catch (error) {
            // Ignore logout errors
            console.warn('Logout request failed:', error);
          }
          
          set((state) => {
            state.isAuthenticated = false;
            state.user = null;
            state.token = null;
            state.refreshToken = null;
            state.tokenExpiration = null;
            state.sessionTimeout = null;
            state.isSessionActive = false;
            state.sessionTimeoutId = null;
            state.error = null;
          });
        },

        // Token management
        setTokens: (token, refreshToken, expiresIn) => {
          const expiration = Date.now() + expiresIn * 1000;
          
          // Store in localStorage via TokenStorage (base64 encoded)
          TokenStorage.setToken(token);
          TokenStorage.setRefreshToken(refreshToken);
          
          set((state) => {
            state.token = token;
            state.refreshToken = refreshToken;
            state.tokenExpiration = expiration;
          });
        },

        refreshTokens: async () => {
          try {
            const newToken = await authService.refreshToken();
            
            set((state) => {
              state.token = newToken;
              state.lastActivity = Date.now();
              state.error = null;
            });
            
            return newToken;
          } catch (error) {
            await get().logout();
            throw error;
          }
        },

        clearTokens: () => {
          get().clearSessionTimeout();
          TokenStorage.clearTokens();
          
          set((state) => {
            state.token = null;
            state.refreshToken = null;
            state.tokenExpiration = null;
            state.isSessionActive = false;
            state.sessionTimeoutId = null;
          });
        },

        // User management
        setUser: (user) => {
          set((state) => {
            state.user = user;
            state.isAuthenticated = true;
          });
        },

        updateUser: (updates) => {
          set((state) => {
            if (state.user) {
              state.user = { ...state.user, ...updates };
            }
          });
        },

        clearUser: () => {
          set((state) => {
            state.user = null;
            state.isAuthenticated = false;
          });
        },

        // Session management
        updateLastActivity: () => {
          const now = Date.now();
          set((state) => {
            state.lastActivity = now;
          });
          
          // Restart session timeout
          get().startSessionTimeout();
        },

        checkSession: () => {
          const { tokenExpiration, token, isSessionActive } = get();
          
          if (!token || !tokenExpiration || !isSessionActive) {
            return false;
          }
          
          const now = Date.now();
          const timeUntilExpiration = tokenExpiration - now;
          
          // If token expires in less than 5 minutes, try to refresh
          if (timeUntilExpiration < AUTH_CONFIG.refreshThreshold) {
            get().refreshTokens().catch(() => {
              get().logout();
            });
          }
          
          return timeUntilExpiration > 0;
        },

        startSessionTimeout: () => {
          const { sessionTimeoutId } = get();
          
          // Clear existing timeout
          if (sessionTimeoutId) {
            clearTimeout(sessionTimeoutId);
          }
          
          // Set new timeout (30 minutes of inactivity)
          const timeoutId = setTimeout(() => {
            get().handleSessionTimeout();
          }, 30 * 60 * 1000); // 30 minutes
          
          set((state) => {
            state.sessionTimeoutId = timeoutId;
          });
        },

        clearSessionTimeout: () => {
          const { sessionTimeoutId } = get();
          
          if (sessionTimeoutId) {
            clearTimeout(sessionTimeoutId);
            set((state) => {
              state.sessionTimeoutId = null;
            });
          }
        },

        handleSessionTimeout: () => {
          set((state) => {
            state.isSessionActive = false;
            state.error = 'Session expired due to inactivity';
          });
          
          // Auto logout after session timeout
          get().logout();
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

        // Utilities
        hasPermission: (permission) => {
          const { user } = get();
          return user?.permissions.includes(permission) || false;
        },

        hasRole: (role) => {
          const { user } = get();
          return user?.roles.includes(role) || false;
        },

        // Reset store
        reset: () => {
          get().clearSessionTimeout();
          get().clearTokens();
          set(defaultState);
        },
      })),
      {
        name: 'iot-devsim-auth-state',
        partialize: (state) => ({
          token: state.token,
          refreshToken: state.refreshToken,
          tokenExpiration: state.tokenExpiration,
          user: state.user,
          isAuthenticated: state.isAuthenticated,
          lastActivity: state.lastActivity,
        }),
      }
    ),
    {
      name: 'auth-store',
    }
  )
);
