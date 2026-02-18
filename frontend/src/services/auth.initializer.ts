/**
 * Authentication Initializer Service
 * Handles app startup authentication logic
 */

import { authService } from './auth.service';
import { useAuthStore } from '@/app/store/auth-store';
import { apiClient } from './api.client';

class AuthInitializer {
  private initialized = false;

  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      // Always set up API client unauthorized callback first
      // This ensures 401 errors will trigger logout even if token is invalid
      apiClient.setUnauthorizedCallback(() => {
        useAuthStore.getState().logout();
      });

      // Check if user has valid tokens
      const isAuthenticated = authService.isAuthenticated();
      
      if (isAuthenticated) {
        // Verify token with server
        const isValid = await authService.verifyToken();
        
        if (isValid) {
          // Start session timeout monitoring
          useAuthStore.getState().startSessionTimeout();
          
          console.log('Authentication restored from storage');
        } else {
          // Token is invalid, clear it
          await useAuthStore.getState().logout();
          console.log('Invalid token cleared');
        }
      }
    } catch (error) {
      console.warn('Auth initialization failed:', error);
      // Clear potentially corrupted auth state
      await useAuthStore.getState().logout();
    } finally {
      this.initialized = true;
    }
  }

  isInitialized(): boolean {
    return this.initialized;
  }

  reset(): void {
    this.initialized = false;
  }
}

// Export singleton instance
export const authInitializer = new AuthInitializer();
