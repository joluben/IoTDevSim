/**
 * Environment Configuration
 * Type-safe environment variables with validation
 */

interface EnvironmentConfig {
  // Application
  NODE_ENV: 'development' | 'production' | 'test';
  DEV: boolean;
  PROD: boolean;
  
  // API Configuration
  VITE_API_BASE_URL: string;
  VITE_WS_URL: string;
  
  // Feature Flags
  VITE_ENABLE_ANALYTICS: boolean;
  VITE_ENABLE_WEBSOCKET: boolean;
  VITE_ENABLE_BETA: boolean;
  
  // External Services
  VITE_SENTRY_DSN?: string;
  VITE_GOOGLE_ANALYTICS_ID?: string;
}

// Default values for development
const defaultConfig: Partial<EnvironmentConfig> = {
  VITE_API_BASE_URL: 'http://localhost:8000/api/v1',
  VITE_WS_URL: 'ws://localhost:8000/ws',
  VITE_ENABLE_ANALYTICS: false,
  VITE_ENABLE_WEBSOCKET: true,
  VITE_ENABLE_BETA: false,
};

// Parse boolean environment variables
const parseBoolean = (value: string | undefined, defaultValue: boolean = false): boolean => {
  if (value === undefined) return defaultValue;
  return value.toLowerCase() === 'true';
};

// Validate required environment variables
const validateEnv = (): EnvironmentConfig => {
  const config: EnvironmentConfig = {
    // Application
    NODE_ENV: (import.meta.env.NODE_ENV as EnvironmentConfig['NODE_ENV']) || 'development',
    DEV: import.meta.env.DEV || false,
    PROD: import.meta.env.PROD || false,
    
    // API Configuration
    VITE_API_BASE_URL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || defaultConfig.VITE_API_BASE_URL!,
    VITE_WS_URL: import.meta.env.VITE_WS_URL || defaultConfig.VITE_WS_URL!,
    
    // Feature Flags
    VITE_ENABLE_ANALYTICS: parseBoolean(import.meta.env.VITE_ENABLE_ANALYTICS, defaultConfig.VITE_ENABLE_ANALYTICS),
    VITE_ENABLE_WEBSOCKET: parseBoolean(import.meta.env.VITE_ENABLE_WEBSOCKET, defaultConfig.VITE_ENABLE_WEBSOCKET),
    VITE_ENABLE_BETA: parseBoolean(import.meta.env.VITE_ENABLE_BETA, defaultConfig.VITE_ENABLE_BETA),
    
    // External Services (optional)
    VITE_SENTRY_DSN: import.meta.env.VITE_SENTRY_DSN,
    VITE_GOOGLE_ANALYTICS_ID: import.meta.env.VITE_GOOGLE_ANALYTICS_ID,
  };

  // Validate required fields in production
  if (config.PROD) {
    const requiredFields: (keyof EnvironmentConfig)[] = [
      'VITE_API_BASE_URL',
      'VITE_WS_URL',
    ];

    for (const field of requiredFields) {
      if (!config[field]) {
        throw new Error(`Missing required environment variable: ${field}`);
      }
    }
  }

  return config;
};

// Export validated configuration
export const env = validateEnv();

// Type guard for checking if we're in development
export const isDevelopment = (): boolean => env.NODE_ENV === 'development';

// Type guard for checking if we're in production
export const isProduction = (): boolean => env.NODE_ENV === 'production';

// Type guard for checking if we're in test environment
export const isTest = (): boolean => env.NODE_ENV === 'test';

// Helper to get API URL with path
export const getApiUrl = (path: string = ''): string => {
  const baseUrl = env.VITE_API_BASE_URL.replace(/\/$/, ''); // Remove trailing slash
  const cleanPath = path.replace(/^\//, ''); // Remove leading slash
  return cleanPath ? `${baseUrl}/${cleanPath}` : baseUrl;
};

// Helper to get WebSocket URL
export const getWsUrl = (path: string = ''): string => {
  const baseUrl = env.VITE_WS_URL.replace(/\/$/, ''); // Remove trailing slash
  const cleanPath = path.replace(/^\//, ''); // Remove leading slash
  return cleanPath ? `${baseUrl}/${cleanPath}` : baseUrl;
};

// Export environment info for debugging
export const getEnvironmentInfo = () => ({
  nodeEnv: env.NODE_ENV,
  isDev: env.DEV,
  isProd: env.PROD,
  apiBaseUrl: env.VITE_API_BASE_URL,
  wsUrl: env.VITE_WS_URL,
  features: {
    analytics: env.VITE_ENABLE_ANALYTICS,
    websocket: env.VITE_ENABLE_WEBSOCKET,
    beta: env.VITE_ENABLE_BETA,
  },
});
