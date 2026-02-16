'use client';

import * as React from 'react';
import { ThemeProvider } from './theme-provider';
import { QueryProvider, useQueryErrorHandler } from './query-provider';
import { I18nProvider } from '@/contexts/i18n-context';
import { AppRouter } from '@/app/router';
import ErrorBoundary from '@/components/common/error-boundary';
import { useAppStore } from '@/app/store';
import { authInitializer } from '@/services/auth.initializer';
import { useActivityTracker } from '@/hooks/useActivityTracker';
import { initializeCSRF } from '@/utils/csrf';
import { initializeCSP } from '@/utils/csp';

interface AppProvidersProps {
  children?: React.ReactNode;
}

// Inner component to handle initialization and error handling
function AppInitializer({ children }: { children: React.ReactNode }) {
  const { initialize, isInitialized, isLoading } = useAppStore();
  const [authInitialized, setAuthInitialized] = React.useState(false);
  
  // Initialize the app and authentication
  React.useEffect(() => {
    const initializeApp = async () => {
      try {
        // Initialize security layers early
        initializeCSP();
        initializeCSRF();

        // Initialize app store
        await initialize();
        
        // Initialize authentication
        await authInitializer.initialize();
        setAuthInitialized(true);
      } catch (error) {
        console.error('App initialization failed:', error);
        setAuthInitialized(true); // Continue even if auth init fails
      }
    };

    initializeApp();
  }, [initialize]);

  // Handle query errors globally
  useQueryErrorHandler();
  
  // Track user activity for session management
  useActivityTracker();

  // Show loading screen during initialization
  if (!isInitialized || !authInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">
            {!isInitialized ? 'Initializing IoT-DevSim v2...' : 'Setting up authentication...'}
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ErrorBoundary>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <QueryProvider>
          <I18nProvider>
            <AppInitializer>
              {children || <AppRouter />}
            </AppInitializer>
          </I18nProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
