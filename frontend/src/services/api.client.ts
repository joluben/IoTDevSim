/**
 * Centralized API Client
 * Axios instance with interceptors for all API communications
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import { API_CONFIG } from '@/app/config/constants';
import { TokenStorage } from './auth.service';
import { csrfAxiosInterceptor, getCSRFHeaders } from '@/utils/csrf';

// API Error types
export interface ApiError {
  message: string;
  status: number;
  code?: string;
  details?: unknown;
}

// API Error response from backend
export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  code?: string;
  details?: unknown;
  errors?: Record<string, string[]>;
}

// Create centralized API client
class ApiClient {
  private api: AxiosInstance;
  private onUnauthorized?: () => void;

  constructor() {
    this.api = axios.create({
      baseURL: API_CONFIG.baseUrl,
      timeout: API_CONFIG.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.api.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add authorization header if token exists
        const token = TokenStorage.getToken();
        if (config.headers) {
          const normalizedToken = typeof token === 'string' ? token.trim() : '';
          const looksLikeJwt = normalizedToken.split('.').length === 3;
          if (normalizedToken && looksLikeJwt) {
            config.headers.Authorization = `Bearer ${normalizedToken}`;
          }
        }

        // Add CSRF headers for state-changing requests
        const mutatingMethods = ['post', 'put', 'patch', 'delete'];
        if (config.method && mutatingMethods.includes(config.method.toLowerCase())) {
          const csrfHeaders = getCSRFHeaders();
          Object.entries(csrfHeaders).forEach(([key, value]) => {
            config.headers.set(key, value);
          });
        }

        // Add timestamp for cache busting if needed
        if (config.method === 'get' && config.params) {
          config.params._t = Date.now();
        }

        return config;
      },
      (error) => {
        return Promise.reject(this.handleError(error));
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // Handle 401 Unauthorized
        if (error.response?.status === 401 && this.onUnauthorized) {
          this.onUnauthorized();
        }

        return Promise.reject(this.handleError(error));
      }
    );

    // Attach CSRF response interceptor to capture token refresh from server
    this.api.interceptors.response.use(
      csrfAxiosInterceptor.response,
      csrfAxiosInterceptor.error
    );
  }

  // Set callback for unauthorized errors
  setUnauthorizedCallback(callback: () => void): void {
    this.onUnauthorized = callback;
  }

  // HTTP Methods
  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.api.get<T>(url, config);
    return response.data;
  }

  async post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.api.post<T>(url, data, config);
    return response.data;
  }

  async put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.api.put<T>(url, data, config);
    return response.data;
  }

  async patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.api.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.api.delete<T>(url, config);
    return response.data;
  }

  // File upload with progress
  async upload<T = unknown>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });

    return response.data;
  }

  // Download file
  async download(url: string, filename?: string): Promise<void> {
    const response = await this.api.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  // Error handling
  private handleError(error: unknown): ApiError {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      const apiError: ApiError = {
        message:
          axiosError.response?.data?.detail ||
          axiosError.response?.data?.message ||
          axiosError.message,
        status: axiosError.response?.status || 0,
        code: axiosError.response?.data?.code,
        details: axiosError.response?.data?.details,
      };
      return apiError;
    }

    return {
      message: error instanceof Error ? error.message : 'An unexpected error occurred',
      status: 0,
    };
  }

  // Get raw axios instance for advanced usage
  getInstance(): AxiosInstance {
    return this.api;
  }

  // Allow registering extra interceptors in a controlled way
  registerInterceptors(
    onRequest?: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig>,
    onResponse?: (response: AxiosResponse<unknown>) => AxiosResponse<unknown> | Promise<AxiosResponse<unknown>>,
  ): void {
    if (onRequest) this.api.interceptors.request.use(onRequest);
    if (onResponse) this.api.interceptors.response.use(onResponse);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
