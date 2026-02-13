import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Home } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ROUTES } from '@/app/config/constants';

export default function UnauthorizedPage() {
  const location = useLocation();
  
  // Get error details from location state
  const message = location.state?.message || 'You do not have permission to access this page.';
  const requiredRole = location.state?.requiredRole;
  const requiredPermission = location.state?.requiredPermission;
  const from = location.state?.from;

  return (
    <div className="flex items-center justify-center min-h-screen bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <CardTitle className="text-xl font-bold">Access Denied</CardTitle>
          <CardDescription>
            You don't have the necessary permissions to view this page
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{message}</AlertDescription>
          </Alert>

          {(requiredRole || requiredPermission) && (
            <div className="text-sm text-muted-foreground space-y-1">
              <p className="font-medium">Required access:</p>
              {requiredRole && (
                <p>• Role: <span className="font-mono">{requiredRole}</span></p>
              )}
              {requiredPermission && (
                <p>• Permission: <span className="font-mono">{requiredPermission}</span></p>
              )}
            </div>
          )}

          <div className="flex flex-col space-y-2">
            {from && (
              <Button variant="outline" asChild className="w-full">
                <Link to={from}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Go back
                </Link>
              </Button>
            )}
            
            <Button asChild className="w-full">
              <Link to={ROUTES.dashboard}>
                <Home className="mr-2 h-4 w-4" />
                Go to Dashboard
              </Link>
            </Button>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            <p>
              Need access? Contact your administrator or{' '}
              <Link
                to="/support"
                className="text-primary hover:underline"
              >
                contact support
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
