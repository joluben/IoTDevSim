'use client';

import * as React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { isDevelopment } from '@/app/config/env';
import { API_CONFIG } from '@/app/config/constants';

interface QueryProviderProps {
  children: React.ReactNode;
}

// Create a client
const createQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Time in milliseconds after data is considered stale
        staleTime: 5 * 60 * 1000, // 5 minutes
        
        // Time in milliseconds that unused/inactive cache data remains in memory
        gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
        
        // Retry failed requests
        retry: (failureCount, error: any) => {
          // Don't retry on 4xx errors (client errors)
          if (error?.status >= 400 && error?.status < 500) {
            return false;
          }
          // Retry up to 3 times for other errors
          return failureCount < API_CONFIG.retryAttempts;
        },
        
        // Retry delay
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        
        // Refetch on window focus in production only
        refetchOnWindowFocus: !isDevelopment(),
        
        // Refetch on reconnect
        refetchOnReconnect: true,
        
        // Refetch on mount if data is stale
        refetchOnMount: true,
      },
      mutations: {
        // Retry failed mutations
        retry: (failureCount, error: any) => {
          // Don't retry on 4xx errors
          if (error?.status >= 400 && error?.status < 500) {
            return false;
          }
          return failureCount < 2; // Retry mutations less aggressively
        },
        
        // Retry delay for mutations
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      },
    },
  });
};

export function QueryProvider({ children }: QueryProviderProps) {
  // Create query client with stable reference
  const [queryClient] = React.useState(() => createQueryClient());

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      queryClient.clear();
    };
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {isDevelopment() && (
        <ReactQueryDevtools
          initialIsOpen={false}
        />
      )}
    </QueryClientProvider>
  );
}

// Custom hook for handling query errors globally
export const useQueryErrorHandler = () => {
  // For now, just a placeholder - will be implemented when needed
  React.useEffect(() => {
    // Global error handling logic will be added here
  }, []);
};

// Utility function to invalidate queries by pattern
export const invalidateQueriesByPattern = (queryClient: QueryClient, pattern: string) => {
  queryClient.invalidateQueries({
    predicate: (query) => {
      return query.queryKey.some((key) => 
        typeof key === 'string' && key.includes(pattern)
      );
    },
  });
};

// Utility function to remove queries by pattern
export const removeQueriesByPattern = (queryClient: QueryClient, pattern: string) => {
  queryClient.removeQueries({
    predicate: (query) => {
      return query.queryKey.some((key) => 
        typeof key === 'string' && key.includes(pattern)
      );
    },
  });
};
