import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { isDevelopment } from '@/app/config/env';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  resetError: () => void;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
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

    // Call the onError callback if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error in development
    if (isDevelopment()) {
      console.error('Error Boundary caught an error:', error, errorInfo);
    }

    // In production, you might want to send this to an error reporting service
    // Example: Sentry.captureException(error, { extra: errorInfo });
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      return (
        <FallbackComponent
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          resetError={this.resetError}
        />
      );
    }

    return this.props.children;
  }
}

// Default error fallback component
function DefaultErrorFallback({ error, errorInfo, resetError }: ErrorFallbackProps) {
  const handleReload = () => {
    window.location.reload();
  };

  const handleGoHome = () => {
    window.location.href = '/';
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <AlertTriangle className="h-16 w-16 text-destructive" />
          </div>
          <CardTitle className="text-2xl">Something went wrong</CardTitle>
          <CardDescription>
            We're sorry, but something unexpected happened. Please try refreshing the page or contact support if the problem persists.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button onClick={resetError} variant="default" className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
            <Button onClick={handleReload} variant="outline" className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              Reload Page
            </Button>
            <Button onClick={handleGoHome} variant="outline" className="flex items-center gap-2">
              <Home className="h-4 w-4" />
              Go Home
            </Button>
          </div>

          {/* Error details in development */}
          {isDevelopment() && error && (
            <details className="mt-6">
              <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground">
                Error Details (Development Only)
              </summary>
              <div className="mt-4 space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-destructive">Error Message:</h4>
                  <pre className="mt-1 text-xs bg-muted p-3 rounded-md overflow-auto">
                    {error.message}
                  </pre>
                </div>
                {error.stack && (
                  <div>
                    <h4 className="text-sm font-medium text-destructive">Stack Trace:</h4>
                    <pre className="mt-1 text-xs bg-muted p-3 rounded-md overflow-auto">
                      {error.stack}
                    </pre>
                  </div>
                )}
                {errorInfo && errorInfo.componentStack && (
                  <div>
                    <h4 className="text-sm font-medium text-destructive">Component Stack:</h4>
                    <pre className="mt-1 text-xs bg-muted p-3 rounded-md overflow-auto">
                      {errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Specialized error boundary for async components
export function AsyncErrorBoundary({ children, onError }: ErrorBoundaryProps) {
  return (
    <ErrorBoundary
      onError={onError}
      fallback={({ error, resetError }) => (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to load component</h3>
          <p className="text-sm text-muted-foreground mb-4">
            There was an error loading this part of the application.
          </p>
          <Button onClick={resetError} size="sm">
            Try Again
          </Button>
          {isDevelopment() && error && (
            <details className="mt-4 text-left">
              <summary className="cursor-pointer text-xs text-muted-foreground">
                Error Details
              </summary>
              <pre className="mt-2 text-xs bg-muted p-2 rounded text-left overflow-auto max-w-md">
                {error.message}
              </pre>
            </details>
          )}
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// Hook for handling errors in functional components
export function useErrorHandler() {
  return React.useCallback((error: Error, errorInfo?: React.ErrorInfo) => {
    if (isDevelopment()) {
      console.error('Error caught by error handler:', error, errorInfo);
    }
    
    // In production, send to error reporting service
    // Example: Sentry.captureException(error, { extra: errorInfo });
  }, []);
}

export default ErrorBoundary;
