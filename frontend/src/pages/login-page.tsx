import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LoginForm } from '@/components/auth/login-form';
import { AuthErrorBoundary } from '@/components/auth/auth-error-boundary';
import { ROUTES } from '@/app/config/constants';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  // Get redirect path from location state or default to dashboard
  const from = location.state?.from || ROUTES.dashboard;

  const handleLoginSuccess = () => {
    // Redirect to the intended page or dashboard
    navigate(from, { replace: true });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-muted/50 p-4">
      <div className="w-full max-w-md">
        <AuthErrorBoundary>
          <LoginForm 
            onSuccess={handleLoginSuccess}
            className="w-full"
          />
        </AuthErrorBoundary>
      </div>
    </div>
  );
}
