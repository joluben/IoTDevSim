/**
 * AuthErrorBoundary Component
 * Error boundary specifically for authentication-related errors
 */

import * as React from 'react';
import { AlertCircle, RefreshCw, LogOut } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuthStore } from '@/app/store/auth-store';

interface AuthErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

interface AuthErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; retry: () => void; logout: () => void }>;
}

export class AuthErrorBoundary extends React.Component<
  AuthErrorBoundaryProps,
  AuthErrorBoundaryState
> {
  constructor(props: AuthErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<AuthErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Log error to monitoring service
    console.error('Auth Error Boundary caught an error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      const { fallback: Fallback } = this.props;
      
      if (Fallback) {
        return (
          <Fallback
            error={this.state.error!}
            retry={this.handleRetry}
            logout={() => {
              // Access auth store logout method
              const { logout } = useAuthStore.getState();
              logout();
            }}
          />
        );
      }

      return <DefaultAuthErrorFallback error={this.state.error!} retry={this.handleRetry} />;
    }

    return this.props.children;
  }
}

// Default fallback component
function DefaultAuthErrorFallback({ 
  error, 
  retry 
}: { 
  error: Error; 
  retry: () => void; 
}) {
  const { logout } = useAuthStore();

  const isAuthError = error.message.includes('401') || 
                     error.message.includes('unauthorized') ||
                     error.message.includes('token') ||
                     error.message.includes('authentication');

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertCircle className="h-6 w-6 text-destructive" />
          </div>
          <CardTitle className="text-xl font-bold">
            {isAuthError ? 'Authentication Error' : 'Something went wrong'}
          </CardTitle>
          <CardDescription>
            {isAuthError 
              ? 'There was a problem with your authentication. Please try signing in again.'
              : 'An unexpected error occurred. Please try again or contact support if the problem persists.'
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              {error.message}
            </AlertDescription>
          </Alert>

          <div className="flex flex-col space-y-2">
            <Button onClick={retry} variant="outline" className="w-full">
              <RefreshCw className="mr-2 h-4 w-4" />
              Try again
            </Button>
            
            {isAuthError && (
              <Button onClick={logout} variant="default" className="w-full">
                <LogOut className="mr-2 h-4 w-4" />
                Sign out and try again
              </Button>
            )}
          </div>

          {process.env.NODE_ENV === 'development' && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-muted-foreground">
                Error details (development only)
              </summary>
              <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto">
                {error.stack}
              </pre>
            </details>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Hook for handling auth errors in components
export function useAuthErrorHandler() {
  const { setError, clearError } = useAuthStore();

  const handleAuthError = React.useCallback((error: unknown) => {
    const errorMessage = error instanceof Error ? error.message : 'An authentication error occurred';
    setError(errorMessage);
  }, [setError]);

  const clearAuthError = React.useCallback(() => {
    clearError();
  }, [clearError]);

  return {
    handleAuthError,
    clearAuthError,
  };
}

export default AuthErrorBoundary;
