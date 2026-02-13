/**
 * Authentication API Service
 * Centralized authentication service with Axios interceptors for JWT token management
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_CONFIG, AUTH_CONFIG } from '@/app/config/constants';

// Types for authentication API responses
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  confirm_password: string;
}

export interface AuthResponse {
  user: {
    id: string;
    email: string;
    name: string;
    avatar?: string;
    role: 'admin' | 'user' | 'viewer';
    permissions: string[];
    createdAt: string;
    lastLoginAt?: string;
  };
  token: string;
  refreshToken: string;
  expiresIn: number; // seconds
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface RefreshTokenResponse {
  token: string;
  refreshToken: string;
  expiresIn: number;
}

// Token storage utilities with encryption consideration
class TokenStorage {
  private static encrypt(value: string): string {
    // In production, implement proper encryption
    // For now, using base64 encoding as basic obfuscation
    return btoa(value);
  }

  private static decrypt(value: string): string {
    try {
      return atob(value);
    } catch {
      return value; // Fallback for unencrypted tokens
    }
  }

  static setToken(token: string): void {
    localStorage.setItem(AUTH_CONFIG.tokenKey, this.encrypt(token));
  }

  static getToken(): string | null {
    const encrypted = localStorage.getItem(AUTH_CONFIG.tokenKey);
    return encrypted ? this.decrypt(encrypted) : null;
  }

  static setRefreshToken(refreshToken: string): void {
    localStorage.setItem(AUTH_CONFIG.refreshTokenKey, this.encrypt(refreshToken));
  }

  static getRefreshToken(): string | null {
    const encrypted = localStorage.getItem(AUTH_CONFIG.refreshTokenKey);
    return encrypted ? this.decrypt(encrypted) : null;
  }

  static clearTokens(): void {
    localStorage.removeItem(AUTH_CONFIG.tokenKey);
    localStorage.removeItem(AUTH_CONFIG.refreshTokenKey);
  }
}

// Authentication API Service Class
class AuthService {
  private api: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value: string) => void;
    reject: (error: any) => void;
  }> = [];

  constructor() {
    // Create Axios instance with base configuration
    this.api = axios.create({
      baseURL: `${API_CONFIG.baseUrl}/auth`,
      timeout: API_CONFIG.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor: Add Authorization header
    this.api.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = TokenStorage.getToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor: Handle token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & {
          _retry?: boolean;
        };

        // Handle 401 Unauthorized errors
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Queue the request while refresh is in progress
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then((token) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              return this.api(originalRequest);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const newToken = await this.refreshToken();
            this.processQueue(null, newToken);
            
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }
            return this.api(originalRequest);
          } catch (refreshError) {
            this.processQueue(refreshError, null);
            this.logout();
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private processQueue(error: any, token: string | null): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token!);
      }
    });

    this.failedQueue = [];
  }

  // Transform raw API response to AuthResponse
  private mapAuthResponse(raw: any): AuthResponse {
    const tokens = raw.tokens || {};
    const user = raw.user || {};
    const mapped: AuthResponse = {
      token: tokens.access_token || raw.token || '',
      refreshToken: tokens.refresh_token || raw.refreshToken || '',
      expiresIn: tokens.expires_in || raw.expiresIn || 1800,
      user: {
        id: user.id || '',
        email: user.email || '',
        name: user.full_name || user.name || '',
        avatar: user.avatar_url || user.avatar,
        role: (user.roles?.[0] as AuthResponse['user']['role']) || 'user',
        permissions: user.permissions || [],
        createdAt: user.created_at || user.createdAt || '',
        lastLoginAt: user.last_login || user.lastLoginAt,
      },
    };
    return mapped;
  }

  // Authentication methods
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await this.api.post('/login', credentials);
      const data = this.mapAuthResponse(response.data);
      
      // Store tokens securely
      TokenStorage.setToken(data.token);
      TokenStorage.setRefreshToken(data.refreshToken);
      
      return data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    try {
      const response = await this.api.post('/register', userData);
      const data = this.mapAuthResponse(response.data);
      
      // Store tokens securely
      TokenStorage.setToken(data.token);
      TokenStorage.setRefreshToken(data.refreshToken);
      
      return data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async refreshToken(): Promise<string> {
    const refreshToken = TokenStorage.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await axios.post<RefreshTokenResponse>(
        `${API_CONFIG.baseUrl}/auth/refresh`,
        { refreshToken },
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: API_CONFIG.timeout,
        }
      );

      const { token, refreshToken: newRefreshToken } = response.data;
      
      // Update stored tokens
      TokenStorage.setToken(token);
      TokenStorage.setRefreshToken(newRefreshToken);
      
      return token;
    } catch (error) {
      TokenStorage.clearTokens();
      throw this.handleError(error);
    }
  }

  async logout(): Promise<void> {
    try {
      const refreshToken = TokenStorage.getRefreshToken();
      if (refreshToken) {
        // Notify server about logout (optional)
        await this.api.post('/logout', { refreshToken });
      }
    } catch (error) {
      // Ignore logout errors, clear tokens anyway
      console.warn('Logout request failed:', error);
    } finally {
      TokenStorage.clearTokens();
    }
  }

  async forgotPassword(email: string): Promise<void> {
    try {
      await this.api.post('/forgot-password', { email });
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async resetPassword(token: string, password: string): Promise<void> {
    try {
      await this.api.post('/reset-password', { token, password });
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async verifyToken(): Promise<boolean> {
    try {
      await this.api.get('/verify');
      return true;
    } catch {
      return false;
    }
  }

  // Utility methods
  isAuthenticated(): boolean {
    const token = TokenStorage.getToken();
    return !!token;
  }

  getToken(): string | null {
    return TokenStorage.getToken();
  }

  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || error.message;
      return new Error(message);
    }
    return error instanceof Error ? error : new Error('An unexpected error occurred');
  }
}

// Export singleton instance
export const authService = new AuthService();
export { TokenStorage };
