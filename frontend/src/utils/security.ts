/**
 * Security Utilities
 * Input sanitization, XSS protection, and security validation utilities
 */

import DOMPurify from 'dompurify';
import { z } from 'zod';

// Configure DOMPurify with secure defaults
const configureDOMPurify = () => {
  // Allow only safe HTML tags and attributes
  DOMPurify.setConfig({
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'u', 'i', 'b',
      'ul', 'ol', 'li', 'a', 'span', 'div',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'blockquote', 'code', 'pre'
    ],
    ALLOWED_ATTR: [
      'href', 'title', 'target', 'rel', 'class', 'id'
    ],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
    SANITIZE_DOM: true,
    KEEP_CONTENT: true,
    // Remove any script-related content
    FORBID_TAGS: ['script', 'object', 'embed', 'form', 'input', 'textarea', 'select', 'button'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur', 'style']
  });
};

// Initialize DOMPurify configuration
configureDOMPurify();

/**
 * Sanitize HTML content to prevent XSS attacks
 */
export const sanitizeHtml = (dirty: string): string => {
  if (!dirty || typeof dirty !== 'string') {
    return '';
  }
  
  return DOMPurify.sanitize(dirty, {
    RETURN_DOM_FRAGMENT: false,
    RETURN_DOM: false
  });
};

/**
 * Sanitize plain text input by removing potentially dangerous characters
 */
export const sanitizeText = (input: string): string => {
  if (!input || typeof input !== 'string') {
    return '';
  }
  
  // Remove null bytes, control characters, and normalize whitespace
  return input
    .replace(/\0/g, '') // Remove null bytes
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '') // Remove control characters
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
};

/**
 * Sanitize URL to prevent javascript: and data: schemes
 */
export const sanitizeUrl = (url: string): string => {
  if (!url || typeof url !== 'string') {
    return '';
  }
  
  const trimmedUrl = url.trim().toLowerCase();
  
  // Block dangerous protocols
  const dangerousProtocols = [
    'javascript:', 'data:', 'vbscript:', 'file:', 'about:',
    'chrome:', 'chrome-extension:', 'moz-extension:'
  ];
  
  for (const protocol of dangerousProtocols) {
    if (trimmedUrl.startsWith(protocol)) {
      return '';
    }
  }
  
  // Allow only http, https, mailto, tel, and relative URLs
  const allowedPatterns = [
    /^https?:\/\//,
    /^mailto:/,
    /^tel:/,
    /^\/[^\/]/,  // Relative URLs starting with /
    /^[^\/]*$/   // Relative URLs without /
  ];
  
  const isAllowed = allowedPatterns.some(pattern => pattern.test(trimmedUrl));
  
  return isAllowed ? url.trim() : '';
};

/**
 * Escape special characters for use in HTML attributes
 */
export const escapeHtmlAttribute = (value: string): string => {
  if (!value || typeof value !== 'string') {
    return '';
  }
  
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\//g, '&#x2F;');
};

/**
 * Validate and sanitize file names
 */
export const sanitizeFileName = (fileName: string): string => {
  if (!fileName || typeof fileName !== 'string') {
    return '';
  }
  
  // Remove path traversal attempts and dangerous characters
  return fileName
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '') // Remove dangerous chars
    .replace(/^\.+/, '') // Remove leading dots
    .replace(/\.+$/, '') // Remove trailing dots
    .replace(/\s+/g, '_') // Replace spaces with underscores
    .substring(0, 255); // Limit length
};

/**
 * Zod schema for secure string validation
 */
export const secureStringSchema = z
  .string()
  .min(1, 'Value is required')
  .max(10000, 'Value is too long')
  .transform((val) => sanitizeText(val))
  .refine((val) => val.length > 0, 'Value cannot be empty after sanitization');

/**
 * Zod schema for secure HTML content
 */
export const secureHtmlSchema = z
  .string()
  .min(1, 'Content is required')
  .max(50000, 'Content is too long')
  .transform((val) => sanitizeHtml(val))
  .refine((val) => val.length > 0, 'Content cannot be empty after sanitization');

/**
 * Zod schema for secure URL validation
 */
export const secureUrlSchema = z
  .string()
  .min(1, 'URL is required')
  .max(2048, 'URL is too long')
  .transform((val) => sanitizeUrl(val))
  .refine((val) => val.length > 0, 'Invalid URL format');

/**
 * Zod schema for secure email validation
 */
export const secureEmailSchema = z
  .string()
  .min(1, 'Email is required')
  .email('Invalid email format')
  .max(254, 'Email is too long')
  .transform((val) => sanitizeText(val.toLowerCase()))
  .refine((val) => {
    // Additional email security checks
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(val);
  }, 'Invalid email format');

/**
 * Zod schema for secure password validation
 */
export const securePasswordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password is too long')
  .refine((val) => /[A-Z]/.test(val), 'Password must contain at least one uppercase letter')
  .refine((val) => /[a-z]/.test(val), 'Password must contain at least one lowercase letter')
  .refine((val) => /\d/.test(val), 'Password must contain at least one number')
  .refine((val) => /[^A-Za-z0-9]/.test(val), 'Password must contain at least one special character')
  .refine((val) => !/\s/.test(val), 'Password cannot contain spaces');

/**
 * Content Security Policy nonce generator
 */
export const generateCSPNonce = (): string => {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

/**
 * Secure random string generator
 */
export const generateSecureToken = (length: number = 32): string => {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

/**
 * Rate limiting helper for client-side protection
 */
export class ClientRateLimiter {
  private attempts: Map<string, { count: number; resetTime: number }> = new Map();
  
  constructor(
    private maxAttempts: number = 5,
    private windowMs: number = 15 * 60 * 1000 // 15 minutes
  ) {}
  
  isAllowed(key: string): boolean {
    const now = Date.now();
    const record = this.attempts.get(key);
    
    if (!record || now > record.resetTime) {
      this.attempts.set(key, { count: 1, resetTime: now + this.windowMs });
      return true;
    }
    
    if (record.count >= this.maxAttempts) {
      return false;
    }
    
    record.count++;
    return true;
  }
  
  reset(key: string): void {
    this.attempts.delete(key);
  }
  
  getRemainingAttempts(key: string): number {
    const record = this.attempts.get(key);
    if (!record || Date.now() > record.resetTime) {
      return this.maxAttempts;
    }
    return Math.max(0, this.maxAttempts - record.count);
  }
}

/**
 * Security headers validation
 */
export const validateSecurityHeaders = (headers: Headers): string[] => {
  const issues: string[] = [];
  
  // Check for important security headers
  const requiredHeaders = [
    'x-content-type-options',
    'x-frame-options',
    'x-xss-protection',
    'referrer-policy',
    'content-security-policy'
  ];
  
  for (const header of requiredHeaders) {
    if (!headers.has(header)) {
      issues.push(`Missing security header: ${header}`);
    }
  }
  
  return issues;
};

/**
 * Input validation for common IoT device data
 */
export const deviceDataSchema = z.object({
  deviceId: z.string()
    .min(1, 'Device ID is required')
    .max(64, 'Device ID is too long')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Device ID contains invalid characters')
    .transform(sanitizeText),
  
  deviceName: z.string()
    .min(1, 'Device name is required')
    .max(100, 'Device name is too long')
    .transform(sanitizeText),
  
  deviceType: z.enum(['sensor', 'actuator', 'gateway', 'controller', 'other'])
    .transform(sanitizeText),
  
  status: z.enum(['online', 'offline', 'error', 'maintenance'])
    .transform(sanitizeText),
  
  metadata: z.record(z.string(), z.any())
    .optional()
    .transform((obj) => {
      if (!obj) return {};
      const sanitized: Record<string, any> = {};
      for (const [key, value] of Object.entries(obj)) {
        const sanitizedKey = sanitizeText(key);
        if (sanitizedKey && typeof value === 'string') {
          sanitized[sanitizedKey] = sanitizeText(value);
        } else if (sanitizedKey) {
          sanitized[sanitizedKey] = value;
        }
      }
      return sanitized;
    })
});

export type DeviceData = z.infer<typeof deviceDataSchema>;
