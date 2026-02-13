/**
 * ProtectedRoute Component
 * Route guard component for authentication and authorization
 * Based on React Router v6 best practices
 */

import * as React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

import { useAuthStore } from '@/app/store/auth-store';
import { ROUTES } from '@/app/config/constants';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'user' | 'viewer';
  requiredPermission?: string;
  fallbackPath?: string;
  showLoader?: boolean;
}

export function ProtectedRoute({
  children,
  requiredRole,
  requiredPermission,
  fallbackPath = ROUTES.login,
  showLoader = true,
}: ProtectedRouteProps) {
  const location = useLocation();
  const { 
    isAuthenticated, 
    isLoading, 
    user, 
    hasRole, 
    hasPermission,
    isSessionActive,
    checkSession 
  } = useAuthStore();

  // Check session validity on mount and periodically
  React.useEffect(() => {
    if (isAuthenticated) {
      checkSession();
    }
  }, [isAuthenticated, checkSession]);

  // Show loading state while authentication is being determined
  if (isLoading && showLoader) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <Navigate
        to={fallbackPath}
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  // Redirect to login if session is not active (expired due to inactivity)
  if (!isSessionActive) {
    return (
      <Navigate
        to={fallbackPath}
        state={{ 
          from: location.pathname,
          message: 'Your session has expired. Please sign in again.'
        }}
        replace
      />
    );
  }

  // Check role requirement
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <Navigate
        to="/unauthorized"
        state={{ 
          from: location.pathname,
          message: `Access denied. ${requiredRole} role required.`,
          requiredRole 
        }}
        replace
      />
    );
  }

  // Check permission requirement
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <Navigate
        to="/unauthorized"
        state={{ 
          from: location.pathname,
          message: `Access denied. ${requiredPermission} permission required.`,
          requiredPermission 
        }}
        replace
      />
    );
  }

  // All checks passed, render children
  return <>{children}</>;
}

// Higher-order component version for easier usage
export function withProtectedRoute<P extends object>(
  Component: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ProtectedRoute {...options}>
      <Component {...props} />
    </ProtectedRoute>
  );

  WrappedComponent.displayName = `withProtectedRoute(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}

// Hook for checking authentication status in components
export function useAuthGuard() {
  const { 
    isAuthenticated, 
    isSessionActive, 
    user, 
    hasRole, 
    hasPermission,
    checkSession 
  } = useAuthStore();

  const canAccess = React.useCallback((
    requiredRole?: string,
    requiredPermission?: string
  ) => {
    if (!isAuthenticated || !isSessionActive) {
      return false;
    }

    if (requiredRole && !hasRole(requiredRole as any)) {
      return false;
    }

    if (requiredPermission && !hasPermission(requiredPermission)) {
      return false;
    }

    return true;
  }, [isAuthenticated, isSessionActive, hasRole, hasPermission]);

  return {
    isAuthenticated,
    isSessionActive,
    user,
    canAccess,
    checkSession,
  };
}

// Export default for lazy loading
export default ProtectedRoute;
