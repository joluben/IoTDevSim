import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Home, ArrowLeft } from 'lucide-react';

export default function NotFoundPage() {
  const handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  const handleGoBack = () => {
    window.history.back();
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <div className="text-6xl font-bold text-muted-foreground mb-4">404</div>
          <CardTitle>Page Not Found</CardTitle>
          <CardDescription>
            The page you're looking for doesn't exist or has been moved.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button onClick={handleGoBack} variant="outline" className="flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              Go Back
            </Button>
            <Button onClick={handleGoHome} className="flex items-center gap-2">
              <Home className="h-4 w-4" />
              Go Home
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
