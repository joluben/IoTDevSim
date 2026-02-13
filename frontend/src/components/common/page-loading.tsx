import React from 'react';
import { Loader2 } from 'lucide-react';

export function PageLoading() {
  return (
    <div className="flex h-screen w-full items-center justify-center">
      <div className="flex flex-col items-center space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <p className="text-muted-foreground">Loading application...</p>
      </div>
    </div>
  );
}
