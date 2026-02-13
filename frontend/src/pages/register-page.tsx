import React from 'react';
import { useNavigate } from 'react-router-dom';
import { RegisterForm } from '@/components/auth/register-form';
import { AuthErrorBoundary } from '@/components/auth/auth-error-boundary';
import { ROUTES } from '@/app/config/constants';

export default function RegisterPage() {
  const navigate = useNavigate();

  const handleRegisterSuccess = () => {
    // Redirect to dashboard after successful registration
    navigate(ROUTES.dashboard, { replace: true });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-muted/50 p-4">
      <div className="w-full max-w-md">
        <AuthErrorBoundary>
          <RegisterForm 
            onSuccess={handleRegisterSuccess}
            className="w-full"
          />
        </AuthErrorBoundary>
      </div>
    </div>
  );
}
