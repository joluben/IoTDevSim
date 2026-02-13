/**
 * Simplified App Providers for Development
 * Minimal providers to get the app running without complex initialization
 */

import * as React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from './theme-provider';
import { QueryProvider } from './query-provider';
import { I18nProvider } from '@/contexts/i18n-context';
import { AppRouter } from '@/app/router';
import ErrorBoundary from '@/components/common/error-boundary';
import { NotificationsToaster } from '@/components/common/notifications-toaster';

interface AppProvidersProps {
  children?: React.ReactNode;
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
            <BrowserRouter>
              {children || <AppRouter />}
            </BrowserRouter>
            <NotificationsToaster />
          </I18nProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
