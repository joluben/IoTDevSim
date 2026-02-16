import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/auth-store';
import AppLayout from '@/components/layout/app-layout';
import AuthLayout from '@/components/layout/auth-layout';
import { PageLoading } from '@/components/common/page-loading';
import ErrorBoundary from '@/components/common/error-boundary';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { AuthErrorBoundary } from '@/components/auth/auth-error-boundary';

// Lazy load page components
const DashboardPage = lazy(() => import('@/pages/dashboard-page'));
const DevicesPage = lazy(() => import('@/pages/devices-page'));
const DeviceFormPage = lazy(() => import('@/pages/device-form-page'));
const ProjectsPage = lazy(() => import('@/pages/projects-page'));
const ProjectDetailPage = lazy(() => import('@/pages/project-detail-page'));
const ProjectFormPage = lazy(() => import('@/pages/project-form-page'));
const ConnectionsPage = lazy(() => import('@/pages/connections-page'));
const DatasetsPage = lazy(() => import('@/pages/datasets-page'));
const AnalyticsPage = lazy(() => import('@/pages/analytics-page'));
const SettingsPage = lazy(() => import('@/pages/settings-page'));
const UsersManagementPage = lazy(() => import('../pages/users-management-page'));
const ProfilePage = lazy(() => import('@/pages/profile-page'));
const LoginPage = lazy(() => import('@/pages/login-page'));
const ForgotPasswordPage = lazy(() => import('@/pages/forgot-password-page'));
const UnauthorizedPage = lazy(() => import('@/pages/unauthorized-page'));
const NotFoundPage = lazy(() => import('@/pages/not-found-page'));

// Root redirect component - smart routing based on auth status
const RootRedirect = () => {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Navigate to="/login" replace />;
};

// Public route component
const PublicRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

// Main router component
export function AppRouter() {
  return (
    <Suspense fallback={<PageLoading />}>
      <ErrorBoundary>
        <AuthErrorBoundary>
          <Routes>
            {/* Root route - redirect based on auth status */}
            <Route path="/" element={<RootRedirect />} />

            {/* Auth routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              } />
              <Route path="/forgot-password" element={
                <PublicRoute>
                  <ForgotPasswordPage />
                </PublicRoute>
              } />
            </Route>

            {/* Protected routes */}
            <Route element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/devices" element={<DevicesPage />} />
              <Route path="/devices/new" element={<DeviceFormPage />} />
              <Route path="/devices/:id/edit" element={<DeviceFormPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/new" element={<ProjectFormPage />} />
              <Route path="/projects/:id/edit" element={<ProjectFormPage />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route path="/connections" element={<ConnectionsPage />} />
              <Route path="/datasets" element={<DatasetsPage />} />
              <Route path="/analytics" element={
                <ProtectedRoute requiredPermission="analytics:view">
                  <AnalyticsPage />
                </ProtectedRoute>
              } />
              <Route path="/settings" element={
                <ProtectedRoute requiredRole="admin">
                  <SettingsPage />
                </ProtectedRoute>
              } />
              <Route path="/settings/users" element={
                <ProtectedRoute requiredPermission="users:read" requiredRole="admin">
                  <UsersManagementPage />
                </ProtectedRoute>
              } />
              <Route path="/profile" element={<ProfilePage />} />
            </Route>

            {/* Unauthorized page */}
            <Route path="/unauthorized" element={<UnauthorizedPage />} />

            {/* 404 Not Found */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthErrorBoundary>
      </ErrorBoundary>
    </Suspense>
  );
}
