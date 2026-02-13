/**
 * Security Logger
 * Client-side security monitoring and reporting utilities
 */

export type SecurityEventLevel = 'info' | 'warn' | 'error' | 'critical';

export interface SecurityEvent {
  level: SecurityEventLevel;
  type: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: number;
}

const SECURITY_REPORT_ENDPOINT = '/api/security-events';

export function logSecurityEvent(event: SecurityEvent): void {
  // Console logging for developers
  const prefix = '[Security]';
  const payload = { ...event, timestamp: event.timestamp || Date.now() };
  
  switch (event.level) {
    case 'info':
      console.info(prefix, payload);
      break;
    case 'warn':
      console.warn(prefix, payload);
      break;
    case 'error':
    case 'critical':
      console.error(prefix, payload);
      break;
  }

  // Best-effort reporting to backend (non-blocking)
  queueMicrotask(() => reportSecurityEvent(payload).catch(() => void 0));
}

export async function reportSecurityEvent(event: SecurityEvent): Promise<void> {
  try {
    await fetch(SECURITY_REPORT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
      keepalive: true, // allow sending on page unload
    });
  } catch {
    // swallow
  }
}

export function attachGlobalSecurityHandlers(): void {
  // Capture unhandled promise rejections
  window.addEventListener('unhandledrejection', (e) => {
    logSecurityEvent({
      level: 'error',
      type: 'unhandled_rejection',
      message: String(e.reason?.message || e.reason || 'Unhandled rejection'),
      details: { stack: e.reason?.stack, reason: e.reason },
      timestamp: Date.now(),
    });
  });

  // Capture script errors
  window.addEventListener('error', (e) => {
    // Ignore generic resource load errors to reduce noise
    if ((e as ErrorEvent).message) {
      logSecurityEvent({
        level: 'error',
        type: 'window_error',
        message: (e as ErrorEvent).message,
        details: {
          filename: (e as ErrorEvent).filename,
          lineno: (e as ErrorEvent).lineno,
          colno: (e as ErrorEvent).colno,
          error: (e as ErrorEvent).error?.toString(),
        },
        timestamp: Date.now(),
      });
    }
  });
}
