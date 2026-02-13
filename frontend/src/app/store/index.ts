/**
 * Global State Management with Zustand
 * Centralized store for application-wide state
 */

export { useAppStore } from './app-store';
export { useAuthStore } from './auth-store';
export { useUIStore } from './ui-store';
export { useDatasetStore } from './dataset-store';
export { useDeviceStore } from './device-store';

export type { AppState, AppActions } from './app-store';
export type { AuthState, AuthActions, User } from './auth-store';
export type { UIState, UIActions } from './ui-store';
export type { DatasetState, DatasetActions } from './dataset-store';
export type { DeviceState, DeviceActions } from './device-store';

