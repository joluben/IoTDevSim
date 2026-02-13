import * as React from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { ROUTES } from '@/app/config/constants';
import { useAuthStore } from '@/app/store';
import ErrorBoundary, { AsyncErrorBoundary } from '@/components/common/error-boundary';

// Lazy load components for code splitting
const DashboardPage = React.lazy(() => import('@/pages/dashboard-page'));
const ConnectionsPage = React.lazy(() => import('@/pages/connections-page'));
const DevicesPage = React.lazy(() => import('@/pages/devices-page'));
const DeviceFormPage = React.lazy(() => import('@/pages/device-form-page'));
const ProjectsPage = React.lazy(() => import('@/pages/projects-page'));
const ProjectDetailPage = React.lazy(() => import('@/pages/project-detail-page'));
const ProjectFormPage = React.lazy(() => import('@/pages/project-form-page'));
const AnalyticsPage = React.lazy(() => import('@/pages/analytics-page'));
const SettingsPage = React.lazy(() => import('@/pages/settings-page'));
const ProfilePage = React.lazy(() => import('@/pages/profile-page'));
const LoginPage = React.lazy(() => import('@/pages/login-page'));
const RegisterPage = React.lazy(() => import('@/pages/register-page'));
const ForgotPasswordPage = React.lazy(() => import('@/pages/forgot-password-page'));
const NotFoundPage = React.lazy(() => import('@/pages/not-found-page'));

// Layout components
const AppLayout = React.lazy(() => import('@/components/layout/app-layout'));
const AuthLayout = React.lazy(() => import('@/components/layout/auth-layout'));

// Loading component for suspense
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

// Protected route wrapper
interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
  requiredRole?: string;
}

function ProtectedRoute({ children, requiredPermission, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, user, hasPermission, hasRole } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.login} replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  if (requiredRole && !hasRole(requiredRole as any)) {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  return <>{children}</>;
}

// Public route wrapper (redirect to dashboard if authenticated)
interface PublicRouteProps {
  children: React.ReactNode;
}

function PublicRoute({ children }: PublicRouteProps) {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  return <>{children}</>;
}

// Suspense wrapper with error boundary
interface SuspenseWrapperProps {
  children: React.ReactNode;
}

function SuspenseWrapper({ children }: SuspenseWrapperProps) {
  return (
    <AsyncErrorBoundary>
      <React.Suspense fallback={<PageLoader />}>
        {children}
      </React.Suspense>
    </AsyncErrorBoundary>
  );
}

// Create router configuration - MUST be synchronous for React Router v7
const router = createBrowserRouter([
  // Public auth routes
  {
    path: ROUTES.login,
    element: (
      <SuspenseWrapper>
        <PublicRoute>
          <AuthLayout />
        </PublicRoute>
      </SuspenseWrapper>
    ),
    children: [{ index: true, element: <LoginPage /> }],
  },
  {
    path: ROUTES.register,
    element: (
      <SuspenseWrapper>
        <PublicRoute>
          <AuthLayout />
        </PublicRoute>
      </SuspenseWrapper>
    ),
    children: [{ index: true, element: <RegisterPage /> }],
  },
  {
    path: ROUTES.forgotPassword,
    element: (
      <SuspenseWrapper>
        <PublicRoute>
          <AuthLayout />
        </PublicRoute>
      </SuspenseWrapper>
    ),
    children: [{ index: true, element: <ForgotPasswordPage /> }],
  },

  // Protected routes with layout - using Outlet pattern
  {
    path: '/',
    element: (
      <SuspenseWrapper>
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      </SuspenseWrapper>
    ),
    children: [
      { index: true, element: <Navigate to={ROUTES.dashboard} replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'connections', element: <ConnectionsPage /> },
      { path: 'connections/:id', element: <ConnectionsPage /> },
      { path: 'datasets', element: <DevicesPage /> },
      { path: 'datasets/:id', element: <DevicesPage /> },
      { path: 'devices', element: <DevicesPage /> },
      { path: 'devices/new', element: <DeviceFormPage /> },
      { path: 'devices/:id/edit', element: <DeviceFormPage /> },
      { path: 'devices/:id', element: <DevicesPage /> },
      { path: 'projects', element: <ProjectsPage /> },
      { path: 'projects/new', element: <ProjectFormPage /> },
      { path: 'projects/:id/edit', element: <ProjectFormPage /> },
      { path: 'projects/:id', element: <ProjectDetailPage /> },
      {
        path: 'analytics',
        element: (
          <ProtectedRoute requiredPermission="analytics:view">
            <AnalyticsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings',
        element: (
          <ProtectedRoute requiredRole="admin">
            <SettingsPage />
          </ProtectedRoute>
        ),
      },
      { path: 'profile', element: <ProfilePage /> },
    ],
  },

  // 404 route
  {
    path: '*',
    element: (
      <SuspenseWrapper>
        <NotFoundPage />
      </SuspenseWrapper>
    ),
  },
]);

// Router provider component
interface AppRouterProps {
  children?: React.ReactNode;
}

export function AppRouter({ children }: AppRouterProps) {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
      {children}
    </ErrorBoundary>
  );
}

// Hook to get current route info
export const useCurrentRoute = () => {
  const location = window.location;
  
  return {
    pathname: location.pathname,
    search: location.search,
    hash: location.hash,
    isProtected: !location.pathname.startsWith('/login') && 
                 !location.pathname.startsWith('/register') && 
                 !location.pathname.startsWith('/forgot-password'),
  };
};

// Navigation helper functions
export const navigationHelpers = {
  goToDashboard: () => window.location.href = ROUTES.dashboard,
  goToLogin: () => window.location.href = ROUTES.login,
  goToConnections: () => window.location.href = ROUTES.connections,
  goToDevices: () => window.location.href = ROUTES.devices,
  goToProjects: () => window.location.href = ROUTES.projects,
  goToAnalytics: () => window.location.href = ROUTES.analytics,
  goToSettings: () => window.location.href = ROUTES.settings,
  goToProfile: () => window.location.href = ROUTES.profile,
};
