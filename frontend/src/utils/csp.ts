/**
 * Content Security Policy (CSP) Utilities
 * CSP configuration and violation reporting for enhanced security
 */

import { generateCSPNonce } from './security';

/**
 * CSP Configuration Interface
 */
interface CSPConfig {
  defaultSrc: string[];
  scriptSrc: string[];
  styleSrc: string[];
  imgSrc: string[];
  connectSrc: string[];
  fontSrc: string[];
  objectSrc: string[];
  mediaSrc: string[];
  frameSrc: string[];
  childSrc: string[];
  workerSrc: string[];
  manifestSrc: string[];
  baseUri: string[];
  formAction: string[];
  frameAncestors: string[];
  upgradeInsecureRequests: boolean;
  blockAllMixedContent: boolean;
  reportUri?: string;
  reportTo?: string;
}

/**
 * Default CSP configuration for IoT-DevSim
 */
const defaultCSPConfig: CSPConfig = {
  defaultSrc: ["'self'"],
  scriptSrc: [
    "'self'",
    "'unsafe-inline'", // Required for React development
    "'unsafe-eval'", // Required for development tools
    "https://cdn.jsdelivr.net",
    "https://unpkg.com"
  ],
  styleSrc: [
    "'self'",
    "'unsafe-inline'", // Required for styled-components and CSS-in-JS
    "https://fonts.googleapis.com",
    "https://cdn.jsdelivr.net"
  ],
  imgSrc: [
    "'self'",
    "data:",
    "blob:",
    "https:",
    "http://localhost:*" // Development only
  ],
  connectSrc: [
    "'self'",
    "https://api.iot-devsim.com",
    "wss://api.iot-devsim.com",
    "http://localhost:*", // Development only
    "ws://localhost:*" // Development only
  ],
  fontSrc: [
    "'self'",
    "https://fonts.gstatic.com",
    "https://cdn.jsdelivr.net",
    "data:"
  ],
  objectSrc: ["'none'"],
  mediaSrc: ["'self'", "blob:", "data:"],
  frameSrc: ["'none'"],
  childSrc: ["'self'"],
  workerSrc: ["'self'", "blob:"],
  manifestSrc: ["'self'"],
  baseUri: ["'self'"],
  formAction: ["'self'"],
  frameAncestors: ["'none'"],
  upgradeInsecureRequests: true,
  blockAllMixedContent: true,
  reportUri: "/api/csp-report"
};

/**
 * Production CSP configuration (more restrictive)
 */
const productionCSPConfig: CSPConfig = {
  ...defaultCSPConfig,
  scriptSrc: [
    "'self'",
    "https://cdn.jsdelivr.net"
  ],
  styleSrc: [
    "'self'",
    "https://fonts.googleapis.com",
    "https://cdn.jsdelivr.net"
  ],
  connectSrc: [
    "'self'",
    "https://api.iot-devsim.com",
    "wss://api.iot-devsim.com"
  ],
  imgSrc: [
    "'self'",
    "data:",
    "blob:",
    "https:"
  ]
};

/**
 * CSP Manager Class
 */
class CSPManager {
  private config: CSPConfig;
  private nonce: string;
  private violations: CSPViolation[] = [];

  constructor(config?: Partial<CSPConfig>) {
    this.config = {
      ...(process.env.NODE_ENV === 'production' ? productionCSPConfig : defaultCSPConfig),
      ...config
    };
    this.nonce = generateCSPNonce();
    this.setupViolationReporting();
  }

  /**
   * Generate CSP header string
   */
  generateCSPHeader(): string {
    const directives: string[] = [];

    // Add each directive
    if (this.config.defaultSrc.length) {
      directives.push(`default-src ${this.config.defaultSrc.join(' ')}`);
    }

    if (this.config.scriptSrc.length) {
      const scriptSrc = [...this.config.scriptSrc];
      // Add nonce for inline scripts
      scriptSrc.push(`'nonce-${this.nonce}'`);
      directives.push(`script-src ${scriptSrc.join(' ')}`);
    }

    if (this.config.styleSrc.length) {
      const styleSrc = [...this.config.styleSrc];
      // Add nonce for inline styles
      styleSrc.push(`'nonce-${this.nonce}'`);
      directives.push(`style-src ${styleSrc.join(' ')}`);
    }

    if (this.config.imgSrc.length) {
      directives.push(`img-src ${this.config.imgSrc.join(' ')}`);
    }

    if (this.config.connectSrc.length) {
      directives.push(`connect-src ${this.config.connectSrc.join(' ')}`);
    }

    if (this.config.fontSrc.length) {
      directives.push(`font-src ${this.config.fontSrc.join(' ')}`);
    }

    if (this.config.objectSrc.length) {
      directives.push(`object-src ${this.config.objectSrc.join(' ')}`);
    }

    if (this.config.mediaSrc.length) {
      directives.push(`media-src ${this.config.mediaSrc.join(' ')}`);
    }

    if (this.config.frameSrc.length) {
      directives.push(`frame-src ${this.config.frameSrc.join(' ')}`);
    }

    if (this.config.childSrc.length) {
      directives.push(`child-src ${this.config.childSrc.join(' ')}`);
    }

    if (this.config.workerSrc.length) {
      directives.push(`worker-src ${this.config.workerSrc.join(' ')}`);
    }

    if (this.config.manifestSrc.length) {
      directives.push(`manifest-src ${this.config.manifestSrc.join(' ')}`);
    }

    if (this.config.baseUri.length) {
      directives.push(`base-uri ${this.config.baseUri.join(' ')}`);
    }

    if (this.config.formAction.length) {
      directives.push(`form-action ${this.config.formAction.join(' ')}`);
    }

    if (this.config.frameAncestors.length) {
      directives.push(`frame-ancestors ${this.config.frameAncestors.join(' ')}`);
    }

    if (this.config.upgradeInsecureRequests) {
      directives.push('upgrade-insecure-requests');
    }

    if (this.config.blockAllMixedContent) {
      directives.push('block-all-mixed-content');
    }

    if (this.config.reportUri) {
      directives.push(`report-uri ${this.config.reportUri}`);
    }

    if (this.config.reportTo) {
      directives.push(`report-to ${this.config.reportTo}`);
    }

    return directives.join('; ');
  }

  /**
   * Get current nonce
   */
  getNonce(): string {
    return this.nonce;
  }

  /**
   * Refresh nonce (should be done on each page load)
   */
  refreshNonce(): string {
    this.nonce = generateCSPNonce();
    return this.nonce;
  }

  /**
   * Setup CSP violation reporting
   */
  private setupViolationReporting(): void {
    document.addEventListener('securitypolicyviolation', (event) => {
      this.handleCSPViolation(event);
    });
  }

  /**
   * Handle CSP violation
   */
  private handleCSPViolation(event: SecurityPolicyViolationEvent): void {
    const violation: CSPViolation = {
      documentURI: event.documentURI,
      referrer: event.referrer,
      blockedURI: event.blockedURI,
      violatedDirective: event.violatedDirective,
      effectiveDirective: event.effectiveDirective,
      originalPolicy: event.originalPolicy,
      sourceFile: event.sourceFile,
      sample: event.sample,
      disposition: event.disposition,
      statusCode: event.statusCode,
      lineNumber: event.lineNumber,
      columnNumber: event.columnNumber,
      timestamp: Date.now()
    };

    this.violations.push(violation);

    // Log violation for debugging
    console.warn('CSP Violation:', violation);

    // Report to server if configured
    if (this.config.reportUri) {
      this.reportViolation(violation);
    }
  }

  /**
   * Report violation to server
   */
  private async reportViolation(violation: CSPViolation): Promise<void> {
    try {
      await fetch(this.config.reportUri!, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          'csp-report': violation
        })
      });
    } catch (error) {
      console.error('Failed to report CSP violation:', error);
    }
  }

  /**
   * Get all violations
   */
  getViolations(): CSPViolation[] {
    return [...this.violations];
  }

  /**
   * Clear violations
   */
  clearViolations(): void {
    this.violations = [];
  }

  /**
   * Update CSP configuration
   */
  updateConfig(newConfig: Partial<CSPConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }
}

/**
 * CSP Violation interface
 */
interface CSPViolation {
  documentURI: string;
  referrer: string;
  blockedURI: string;
  violatedDirective: string;
  effectiveDirective: string;
  originalPolicy: string;
  sourceFile: string;
  sample: string;
  disposition: SecurityPolicyViolationEventDisposition;
  statusCode: number;
  lineNumber: number;
  columnNumber: number;
  timestamp: number;
}

// Singleton CSP Manager
export const cspManager = new CSPManager();

/**
 * Initialize CSP
 */
export const initializeCSP = (config?: Partial<CSPConfig>): void => {
  if (config) {
    cspManager.updateConfig(config);
  }

  // Set CSP meta tag if not already set by server
  if (!document.querySelector('meta[http-equiv="Content-Security-Policy"]')) {
    const meta = document.createElement('meta');
    meta.httpEquiv = 'Content-Security-Policy';
    meta.content = cspManager.generateCSPHeader();
    document.head.appendChild(meta);
  }
};

/**
 * Get CSP nonce for inline scripts/styles
 */
export const getCSPNonce = (): string => {
  return cspManager.getNonce();
};

/**
 * Hook for CSP utilities
 */
export const useCSP = () => {
  const getNonce = () => cspManager.getNonce();
  const getViolations = () => cspManager.getViolations();
  const clearViolations = () => cspManager.clearViolations();

  return {
    getNonce,
    getViolations,
    clearViolations
  };
};

/**
 * Validate if a URL is allowed by CSP
 */
export const isUrlAllowedByCSP = (url: string, directive: keyof CSPConfig): boolean => {
  const config = cspManager['config'];
  const allowedSources = config[directive] as string[];

  if (!allowedSources) return false;

  // Check for 'self'
  if (allowedSources.includes("'self'")) {
    try {
      const urlObj = new URL(url);
      const currentOrigin = window.location.origin;
      if (urlObj.origin === currentOrigin) {
        return true;
      }
    } catch {
      // Invalid URL
      return false;
    }
  }

  // Check for wildcard https:
  if (allowedSources.includes('https:') && url.startsWith('https:')) {
    return true;
  }

  // Check for wildcard http:
  if (allowedSources.includes('http:') && url.startsWith('http:')) {
    return true;
  }

  // Check for data: URLs
  if (allowedSources.includes('data:') && url.startsWith('data:')) {
    return true;
  }

  // Check for blob: URLs
  if (allowedSources.includes('blob:') && url.startsWith('blob:')) {
    return true;
  }

  // Check for exact matches
  return allowedSources.some(source => {
    if (source.startsWith("'") && source.endsWith("'")) {
      return false; // Skip special keywords
    }
    return url.startsWith(source);
  });
};

export { CSPManager, type CSPConfig, type CSPViolation };
