/**
 * CSRF Protection Utilities
 * Cross-Site Request Forgery protection for React applications
 */

import { generateSecureToken } from './security';

// CSRF token storage key
const CSRF_TOKEN_KEY = 'iot-devsim-csrf-token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

/**
 * CSRF Token Manager
 */
class CSRFTokenManager {
  private token: string | null = null;
  private tokenExpiry: number = 0;
  private readonly tokenLifetime = 60 * 60 * 1000; // 1 hour

  /**
   * Get current CSRF token, generate new one if expired
   */
  getToken(): string {
    const now = Date.now();
    
    if (!this.token || now > this.tokenExpiry) {
      this.generateNewToken();
    }
    
    return this.token!;
  }

  /**
   * Generate a new CSRF token
   */
  private generateNewToken(): void {
    this.token = generateSecureToken(32);
    this.tokenExpiry = Date.now() + this.tokenLifetime;
    
    // Store in sessionStorage (more secure than localStorage for CSRF tokens)
    try {
      sessionStorage.setItem(CSRF_TOKEN_KEY, JSON.stringify({
        token: this.token,
        expiry: this.tokenExpiry
      }));
    } catch (error) {
      console.warn('Failed to store CSRF token:', error);
    }
  }

  /**
   * Initialize token from storage
   */
  initialize(): void {
    try {
      const stored = sessionStorage.getItem(CSRF_TOKEN_KEY);
      if (stored) {
        const { token, expiry } = JSON.parse(stored);
        const now = Date.now();
        
        if (token && expiry && now < expiry) {
          this.token = token;
          this.tokenExpiry = expiry;
          return;
        }
      }
    } catch (error) {
      console.warn('Failed to load CSRF token from storage:', error);
    }
    
    // Generate new token if none found or expired
    this.generateNewToken();
  }

  /**
   * Refresh the token (force generation of new token)
   */
  refreshToken(): string {
    this.generateNewToken();
    return this.token!;
  }

  /**
   * Clear the token
   */
  clearToken(): void {
    this.token = null;
    this.tokenExpiry = 0;
    
    try {
      sessionStorage.removeItem(CSRF_TOKEN_KEY);
    } catch (error) {
      console.warn('Failed to clear CSRF token:', error);
    }
  }

  /**
   * Validate a token
   */
  validateToken(token: string): boolean {
    return token === this.token && Date.now() < this.tokenExpiry;
  }

  /**
   * Update token values from server response in a safe way
   */
  updateFromServer(token: string, lifetimeMs: number = this.tokenLifetime): void {
    this.token = token;
    this.tokenExpiry = Date.now() + lifetimeMs;
    try {
      sessionStorage.setItem(CSRF_TOKEN_KEY, JSON.stringify({ token: this.token, expiry: this.tokenExpiry }));
    } catch {
      // ignore storage errors
    }
  }
}

// Singleton instance
export const csrfTokenManager = new CSRFTokenManager();

/**
 * Initialize CSRF protection
 */
export const initializeCSRF = (): void => {
  csrfTokenManager.initialize();
};

/**
 * Get CSRF token for API requests
 */
export const getCSRFToken = (): string => {
  return csrfTokenManager.getToken();
};

/**
 * Get CSRF headers for API requests
 */
export const getCSRFHeaders = (): Record<string, string> => {
  return {
    [CSRF_HEADER_NAME]: getCSRFToken()
  };
};

/**
 * Axios interceptor for automatic CSRF token inclusion
 */
export const csrfAxiosInterceptor = {
  request: (config: any) => {
    // Add CSRF token to state-changing requests
    const stateMutatingMethods = ['post', 'put', 'patch', 'delete'];
    
    if (config.method && stateMutatingMethods.includes(config.method.toLowerCase())) {
      config.headers = {
        ...config.headers,
        ...getCSRFHeaders()
      };
    }
    
    return config;
  },
  
  response: (response: any) => {
    // Check if server sent a new CSRF token
    const newToken = response.headers['x-csrf-token'] || response.headers['X-CSRF-Token'];
    if (newToken) {
      // Update our token if server provided a new one
      csrfTokenManager.updateFromServer(newToken as string, 60 * 60 * 1000);
    }
    
    return response;
  },
  
  error: (error: any) => {
    // If we get a CSRF error, refresh the token
    if (error.response?.status === 403 && 
        error.response?.data?.message?.includes('CSRF')) {
      csrfTokenManager.refreshToken();
    }
    
    return Promise.reject(error);
  }
};

/**
 * React-style hook bridge (no JSX) for CSRF usage in components
 * Components can import this from a TS/TSX file and call these helpers.
 */
export const useCSRFHelpers = () => {
  const getToken = () => csrfTokenManager.getToken();
  const refreshToken = () => csrfTokenManager.refreshToken();
  const getHeaders = () => getCSRFHeaders();
  const getHiddenInputProps = () => ({ name: '_csrf', value: getToken() });
  return { getToken, refreshToken, getHeaders, getHiddenInputProps };
};

/**
 * Create a hidden input DOM element for CSRF token (no JSX)
 */
export const createCSRFHiddenInput = (): HTMLInputElement => {
  const input = document.createElement('input');
  input.type = 'hidden';
  input.name = '_csrf';
  input.value = getCSRFToken();
  input.setAttribute('aria-hidden', 'true');
  return input;
};

/**
 * Validate CSRF token from form data
 */
export const validateCSRFFromForm = (formData: FormData): boolean => {
  const token = formData.get('_csrf') as string;
  return csrfTokenManager.validateToken(token);
};

/**
 * SameSite cookie configuration for CSRF protection
 */
export const getSecureCookieConfig = () => {
  return {
    sameSite: 'strict' as const,
    secure: window.location.protocol === 'https:',
    httpOnly: false, // Must be false for client-side access
    maxAge: 60 * 60, // 1 hour
    path: '/'
  };
};

/**
 * Double Submit Cookie pattern implementation
 */
export const doubleSubmitCookie = {
  /**
   * Set CSRF cookie
   */
  setCookie: (token: string) => {
    const config = getSecureCookieConfig();
    const cookieString = [
      `csrf-token=${token}`,
      `Max-Age=${config.maxAge}`,
      `Path=${config.path}`,
      `SameSite=${config.sameSite}`,
      config.secure ? 'Secure' : ''
    ].filter(Boolean).join('; ');
    
    document.cookie = cookieString;
  },
  
  /**
   * Get CSRF cookie value
   */
  getCookie: (): string | null => {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrf-token') {
        return value;
      }
    }
    return null;
  },
  
  /**
   * Clear CSRF cookie
   */
  clearCookie: () => {
    document.cookie = 'csrf-token=; Max-Age=0; Path=/; SameSite=strict';
  }
};

/**
 * Referrer validation for additional CSRF protection
 */
export const validateReferrer = (allowedOrigins: string[]): boolean => {
  const referrer = document.referrer;
  
  if (!referrer) {
    // No referrer might be suspicious, but can be legitimate
    return true; // Let server decide
  }
  
  try {
    const referrerUrl = new URL(referrer);
    const currentOrigin = window.location.origin;
    
    // Allow same origin
    if (referrerUrl.origin === currentOrigin) {
      return true;
    }
    
    // Check against allowed origins
    return allowedOrigins.includes(referrerUrl.origin);
  } catch (error) {
    // Invalid referrer URL
    return false;
  }
};

/**
 * Origin validation for CSRF protection
 */
export const validateOrigin = (allowedOrigins: string[]): boolean => {
  const currentOrigin = window.location.origin;
  return allowedOrigins.includes(currentOrigin);
};
