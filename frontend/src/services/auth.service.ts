/**
 * Authentication API Service
 * Centralized authentication service with Axios interceptors for JWT token management
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_CONFIG, AUTH_CONFIG, FEATURES } from '@/app/config/constants';

// Types for authentication API responses
export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  user: {
    id: string;
    email: string;
    name: string;
    avatar?: string;
    roles: string[];
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

export interface UserProfileResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  avatar_url?: string | null;
  bio?: string | null;
  roles: string[];
  permissions: string[];
  created_at: string;
  last_login?: string | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

interface LogoutStrategy {
  logout(api: AxiosInstance): Promise<void>;
}

class LocalLogoutStrategy implements LogoutStrategy {
  async logout(api: AxiosInstance): Promise<void> {
    const refreshToken = TokenStorage.getRefreshToken();
    if (!refreshToken) {
      return;
    }

    await api.post('/logout', { refreshToken });
  }
}

class FederatedLogoutStrategy implements LogoutStrategy {
  constructor(private readonly fallbackStrategy: LogoutStrategy) {}

  async logout(api: AxiosInstance): Promise<void> {
    // Phase 2 placeholder: local logout remains active until federated flow is enabled.
    await this.fallbackStrategy.logout(api);
  }
}

const buildLogoutStrategy = (): LogoutStrategy => {
  const localStrategy = new LocalLogoutStrategy();
  return FEATURES.enableFederatedAuth
    ? new FederatedLogoutStrategy(localStrategy)
    : localStrategy;
};

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
  private logoutStrategy: LogoutStrategy;
  private failedQueue: Array<{
    resolve: (value: string) => void;
    reject: (error: Error) => void;
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
    this.logoutStrategy = buildLogoutStrategy();
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
            const typedError = refreshError instanceof Error ? refreshError : new Error(String(refreshError));
            this.processQueue(typedError, null);
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

  private processQueue(error: Error | null, token: string | null): void {
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
  private mapAuthResponse(raw: unknown): AuthResponse {
    const rawData = raw as Record<string, unknown>;
    const tokens = (rawData.tokens as Record<string, unknown>) || {};
    const user = (rawData.user as Record<string, unknown>) || {};
    const mapped: AuthResponse = {
      token: (tokens.access_token as string) || (rawData.token as string) || '',
      refreshToken: (tokens.refresh_token as string) || (rawData.refreshToken as string) || '',
      expiresIn: (tokens.expires_in as number) || (rawData.expiresIn as number) || 1800,
      user: {
        id: (user.id as string) || '',
        email: (user.email as string) || '',
        name: (user.full_name as string) || (user.name as string) || '',
        avatar: (user.avatar_url as string) || (user.avatar as string),
        roles: (user.roles as string[]) || ['user'],
        permissions: (user.permissions as string[]) || [],
        createdAt: (user.created_at as string) || (user.createdAt as string) || '',
        lastLoginAt: (user.last_login as string) || (user.lastLoginAt as string),
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
      await this.logoutStrategy.logout(this.api);
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

  async getCurrentProfile(): Promise<UserProfileResponse> {
    try {
      const response = await this.api.get<UserProfileResponse>('/me');
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async changePassword(payload: ChangePasswordRequest): Promise<void> {
    try {
      await this.api.post('/change-password', payload);
    } catch (error) {
      throw this.handleError(error);
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

  private handleError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<{ message?: string }>;
      const message = axiosError.response?.data?.message || axiosError.message;
      return new Error(message);
    }
    return error instanceof Error ? error : new Error('An unexpected error occurred');
  }
}

// Export singleton instance
export const authService = new AuthService();
export { TokenStorage };
