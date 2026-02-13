import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { STORAGE_KEYS } from '@/app/config/constants';

// UI state interface
export interface UIState {
  // Layout
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  
  // Navigation
  currentPage: string;
  breadcrumbs: Array<{ label: string; href?: string }>;
  
  // Modals and dialogs
  modals: Record<string, boolean>;
  
  // Notifications
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message?: string;
    duration?: number;
    timestamp: number;
  }>;
  
  // Loading states
  loadingStates: Record<string, boolean>;
  
  // Table settings
  tableSettings: Record<string, {
    pageSize: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    filters?: Record<string, any>;
    hiddenColumns?: string[];
  }>;
  
  // Dashboard layout
  dashboardLayout: Array<{
    id: string;
    x: number;
    y: number;
    w: number;
    h: number;
    component: string;
  }>;
  
  // Search
  globalSearch: {
    query: string;
    isOpen: boolean;
    results: any[];
    isLoading: boolean;
  };
}

// UI actions interface
export interface UIActions {
  // Layout
  setSidebarOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  toggleSidebarCollapsed: () => void;
  
  // Navigation
  setCurrentPage: (page: string) => void;
  setBreadcrumbs: (breadcrumbs: UIState['breadcrumbs']) => void;
  
  // Modals and dialogs
  openModal: (modalId: string) => void;
  closeModal: (modalId: string) => void;
  toggleModal: (modalId: string) => void;
  closeAllModals: () => void;
  
  // Notifications
  addNotification: (notification: Omit<UIState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  
  // Loading states
  setLoading: (key: string, loading: boolean) => void;
  clearLoading: (key: string) => void;
  clearAllLoading: () => void;
  
  // Table settings
  updateTableSettings: (tableId: string, settings: Partial<UIState['tableSettings'][string]>) => void;
  resetTableSettings: (tableId: string) => void;
  
  // Dashboard layout
  updateDashboardLayout: (layout: UIState['dashboardLayout']) => void;
  resetDashboardLayout: () => void;
  
  // Search
  setGlobalSearch: (updates: Partial<UIState['globalSearch']>) => void;
  clearGlobalSearch: () => void;
  
  // Reset store
  reset: () => void;
}

// Combined state and actions
export type UIStore = UIState & UIActions;

// Default state
const defaultState: UIState = {
  sidebarOpen: true,
  sidebarCollapsed: false,
  currentPage: '/',
  breadcrumbs: [],
  modals: {},
  notifications: [],
  loadingStates: {},
  tableSettings: {},
  dashboardLayout: [],
  globalSearch: {
    query: '',
    isOpen: false,
    results: [],
    isLoading: false,
  },
};

// Create the store
export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...defaultState,

        // Layout
        setSidebarOpen: (open) => {
          set((state) => {
            state.sidebarOpen = open;
          });
        },

        setSidebarCollapsed: (collapsed) => {
          set((state) => {
            state.sidebarCollapsed = collapsed;
          });
        },

        toggleSidebar: () => {
          set((state) => {
            state.sidebarOpen = !state.sidebarOpen;
          });
        },

        toggleSidebarCollapsed: () => {
          set((state) => {
            state.sidebarCollapsed = !state.sidebarCollapsed;
          });
        },

        // Navigation
        setCurrentPage: (page) => {
          set((state) => {
            state.currentPage = page;
          });
        },

        setBreadcrumbs: (breadcrumbs) => {
          set((state) => {
            state.breadcrumbs = breadcrumbs;
          });
        },

        // Modals and dialogs
        openModal: (modalId) => {
          set((state) => {
            state.modals[modalId] = true;
          });
        },

        closeModal: (modalId) => {
          set((state) => {
            state.modals[modalId] = false;
          });
        },

        toggleModal: (modalId) => {
          set((state) => {
            state.modals[modalId] = !state.modals[modalId];
          });
        },

        closeAllModals: () => {
          set((state) => {
            Object.keys(state.modals).forEach(key => {
              state.modals[key] = false;
            });
          });
        },

        // Notifications
        addNotification: (notification) => {
          const id = Math.random().toString(36).substr(2, 9);
          const timestamp = Date.now();
          
          set((state) => {
            state.notifications.push({
              ...notification,
              id,
              timestamp,
            });
          });

          // Auto-remove notification after duration
          if (notification.duration !== 0) {
            const duration = notification.duration || 5000;
            setTimeout(() => {
              get().removeNotification(id);
            }, duration);
          }
        },

        removeNotification: (id) => {
          set((state) => {
            state.notifications = state.notifications.filter((notification: UIState['notifications'][0]) => notification.id !== id);
          });
        },

        clearNotifications: () => {
          set((state) => {
            state.notifications = [];
          });
        },

        // Loading states
        setLoading: (key, loading) => {
          set((state) => {
            state.loadingStates[key] = loading;
          });
        },

        clearLoading: (key) => {
          set((state) => {
            delete state.loadingStates[key];
          });
        },

        clearAllLoading: () => {
          set((state) => {
            state.loadingStates = {};
          });
        },

        // Table settings
        updateTableSettings: (tableId, settings) => {
          set((state) => {
            if (!state.tableSettings[tableId]) {
              state.tableSettings[tableId] = {
                pageSize: 20,
              };
            }
            state.tableSettings[tableId] = {
              ...state.tableSettings[tableId],
              ...settings,
            };
          });
        },

        resetTableSettings: (tableId) => {
          set((state) => {
            delete state.tableSettings[tableId];
          });
        },

        // Dashboard layout
        updateDashboardLayout: (layout) => {
          set((state) => {
            state.dashboardLayout = layout;
          });
        },

        resetDashboardLayout: () => {
          set((state) => {
            state.dashboardLayout = [];
          });
        },

        // Search
        setGlobalSearch: (updates) => {
          set((state) => {
            state.globalSearch = { ...state.globalSearch, ...updates };
          });
        },

        clearGlobalSearch: () => {
          set((state) => {
            state.globalSearch = {
              query: '',
              isOpen: false,
              results: [],
              isLoading: false,
            };
          });
        },

        // Reset store
        reset: () => {
          set(defaultState);
        },
      })),
      {
        name: STORAGE_KEYS.dashboardLayout,
        partialize: (state) => ({
          sidebarCollapsed: state.sidebarCollapsed,
          tableSettings: state.tableSettings,
          dashboardLayout: state.dashboardLayout,
        }),
      }
    ),
    {
      name: 'ui-store',
    }
  )
);
