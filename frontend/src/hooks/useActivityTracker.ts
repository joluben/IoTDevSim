/**
 * Activity Tracker Hook
 * Tracks user activity and manages session timeout automatically
 */

import { useEffect, useCallback } from 'react';
import { useAuthStore } from '@/app/store/auth-store';

// Events that indicate user activity
const ACTIVITY_EVENTS = [
  'mousedown',
  'mousemove',
  'keypress',
  'scroll',
  'touchstart',
  'click',
] as const;

// Throttle delay for activity updates (to avoid excessive calls)
const THROTTLE_DELAY = 30000; // 30 seconds

export function useActivityTracker() {
  const { isAuthenticated, updateLastActivity } = useAuthStore();

  // Throttled activity update function
  const throttledUpdateActivity = useCallback(() => {
    let lastUpdate = 0;
    
    return () => {
      const now = Date.now();
      if (now - lastUpdate > THROTTLE_DELAY) {
        lastUpdate = now;
        updateLastActivity();
      }
    };
  }, [updateLastActivity]);

  const handleActivity = throttledUpdateActivity();

  useEffect(() => {
    // Only track activity if user is authenticated
    if (!isAuthenticated) {
      return;
    }

    // Add event listeners for activity tracking
    ACTIVITY_EVENTS.forEach((event) => {
      document.addEventListener(event, handleActivity, { passive: true });
    });

    // Cleanup event listeners
    return () => {
      ACTIVITY_EVENTS.forEach((event) => {
        document.removeEventListener(event, handleActivity);
      });
    };
  }, [isAuthenticated, handleActivity]);

  // Return activity tracking status
  return {
    isTracking: isAuthenticated,
  };
}

// Hook for manual activity updates (useful for API calls, etc.)
export function useManualActivityUpdate() {
  const { updateLastActivity } = useAuthStore();

  return useCallback(() => {
    updateLastActivity();
  }, [updateLastActivity]);
}
