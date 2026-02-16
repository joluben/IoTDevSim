/**
 * Application Constants
 * Centralized configuration for the IoTDevSim Frontend
 */

// Application Information
export const APP_CONFIG = {
  name: 'IoTDevSim',
  version: '1.0.0',
  description: 'IoT Device Simulation Platform',
  author: 'IoTDevSim Team',
} as const;

// API Configuration
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000, // 30 seconds
  retryAttempts: 3,
  retryDelay: 1000, // 1 second
} as const;

// WebSocket Configuration
export const WS_CONFIG = {
  url: import.meta.env.VITE_WS_URL || 'ws://localhost:3000/ws',
  reconnectInterval: 5000, // 5 seconds
  maxReconnectAttempts: 10,
  heartbeatInterval: 30000, // 30 seconds
} as const;

// Authentication Configuration
export const AUTH_CONFIG = {
  tokenKey: 'iotdevsim-token',
  refreshTokenKey: 'iotdevsim-refresh-token',
  tokenExpiration: 24 * 60 * 60 * 1000, // 24 hours
  refreshThreshold: 5 * 60 * 1000, // 5 minutes before expiration
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  theme: 'iotdevsim-theme',
  language: 'iotdevsim-language',
  userPreferences: 'iotdevsim-user-preferences',
  dashboardLayout: 'iotdevsim-dashboard-layout',
  tableSettings: 'iotdevsim-table-settings',
} as const;

// Route Paths
export const ROUTES = {
  // Public routes
  home: '/',
  login: '/login',
  forgotPassword: '/forgot-password',

  // Protected routes
  dashboard: '/dashboard',
  connections: '/connections',
  datasets: '/datasets',
  devices: '/devices',
  projects: '/projects',
  analytics: '/analytics',
  settings: '/settings',
  usersManagement: '/settings/users',
  profile: '/profile',

  // Nested routes
  connectionDetails: '/connections/:id',
  datasetDetails: '/datasets/:id',
  deviceDetails: '/devices/:id',
  deviceNew: '/devices/new',
  deviceEdit: '/devices/:id/edit',
  projectDetails: '/projects/:id',
  projectNew: '/projects/new',
  projectEdit: '/projects/:id/edit',
} as const;

// Device Status Types
export const DEVICE_STATUS = {
  online: 'online',
  offline: 'offline',
  error: 'error',
  warning: 'warning',
  maintenance: 'maintenance',
} as const;

// Connection Types
export const CONNECTION_TYPES = {
  mqtt: 'MQTT',
  https: 'HTTPS',
  kafka: 'Kafka',
  websocket: 'WebSocket',
  tcp: 'TCP',
  udp: 'UDP',
} as const;

// Project Status Types
export const PROJECT_STATUS = {
  draft: 'draft',
  active: 'active',
  paused: 'paused',
  completed: 'completed',
  archived: 'archived',
} as const;

// Pagination Configuration
export const PAGINATION = {
  defaultPageSize: 20,
  pageSizeOptions: [10, 20, 50, 100],
  maxPageSize: 1000,
} as const;

// File Upload Configuration
export const FILE_UPLOAD = {
  maxSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: {
    csv: ['text/csv', 'application/csv'],
    json: ['application/json'],
    image: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  },
  chunkSize: 1024 * 1024, // 1MB chunks for large files
} as const;

// Validation Rules
export const VALIDATION = {
  password: {
    minLength: 8,
    maxLength: 128,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecialChars: true,
  },
  deviceName: {
    minLength: 2,
    maxLength: 50,
    pattern: /^[a-zA-Z0-9_-]+$/,
  },
  projectName: {
    minLength: 2,
    maxLength: 100,
  },
} as const;

// Chart Configuration
export const CHART_CONFIG = {
  colors: {
    primary: 'hsl(217 91% 60%)',
    success: 'hsl(142 76% 36%)',
    warning: 'hsl(32 95% 44%)',
    error: 'hsl(0 84% 60%)',
    info: 'hsl(221 83% 53%)',
  },
  animation: {
    duration: 300,
    easing: 'ease-in-out',
  },
} as const;

// Feature Flags
export const FEATURES = {
  enableAnalytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  enableWebSocket: import.meta.env.VITE_ENABLE_WEBSOCKET !== 'false',
  enableDevTools: import.meta.env.DEV,
  enableBetaFeatures: import.meta.env.VITE_ENABLE_BETA === 'true',
  enableFederatedAuth: import.meta.env.VITE_ENABLE_FEDERATED_AUTH === 'true',
  federatedAuthProvider: import.meta.env.VITE_FEDERATED_AUTH_PROVIDER || 'Keycloak',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  network: 'Network error. Please check your connection.',
  unauthorized: 'You are not authorized to perform this action.',
  forbidden: 'Access denied.',
  notFound: 'The requested resource was not found.',
  serverError: 'Internal server error. Please try again later.',
  validationError: 'Please check your input and try again.',
  timeout: 'Request timed out. Please try again.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  created: 'Successfully created.',
  updated: 'Successfully updated.',
  deleted: 'Successfully deleted.',
  saved: 'Successfully saved.',
  connected: 'Successfully connected.',
  disconnected: 'Successfully disconnected.',
} as const;
