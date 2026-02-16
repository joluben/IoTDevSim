import React from 'react';
import { ForgotPasswordForm } from '@/components/auth/forgot-password-form';
import { AuthErrorBoundary } from '@/components/auth/auth-error-boundary';

export default function ForgotPasswordPage() {
  const handleResetSuccess = (email: string) => {
    console.log(`Password reset email sent to: ${email}`);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-muted/50 p-4">
      <div className="w-full max-w-md">
        <AuthErrorBoundary>
          <ForgotPasswordForm 
            onSuccess={handleResetSuccess}
            className="w-full"
          />
        </AuthErrorBoundary>
      </div>
    </div>
  );
}
